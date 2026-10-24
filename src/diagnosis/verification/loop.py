"""Agentic Self-Verification Loop for FaultSense (Phase 6).

Coordinates:
Initial Retrieval -> Draft Diagnosis -> Evidence Verification -> Sufficient Evidence?
If Sufficient: Finalize & Preserve Audit Record.
If Insufficient: Refine Query/Expand Retrieval -> Regenerate -> Re-Verify.
If Retry Limit Reached: Explicit Inconclusive / Insufficient Evidence Result.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from config.settings import Settings, get_settings
from src.diagnosis.fallback import DeterministicFallbackEngine
from src.diagnosis.llm.base import BaseLLMProvider
from src.diagnosis.prompt_builder import DiagnosticPromptBuilder
from src.diagnosis.schema import CandidateCause, DiagnosticReport, DiagnosticStatus, ProbabilityBand
from src.diagnosis.session import DiagnosisRequest
from src.diagnosis.validator import DiagnosticValidator
from src.diagnosis.verification.schema import (
    ClaimStatus,
    VerificationHistoryStep,
    VerificationRecord,
    VerificationResult,
    VerificationVerdict,
)
from src.diagnosis.verification.service import DiagnosisVerificationService
from src.retrieval.evidence import EvidencePackage, EvidenceSufficiencyLevel
from src.retrieval.ranking import FilterMode
from src.retrieval.retrieval_service import FaultRetrievalService
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AgenticVerificationLoop:
    """Manages the agentic self-verification and iterative refinement loop."""

    def __init__(
        self,
        retrieval_service: FaultRetrievalService,
        verification_service: DiagnosisVerificationService,
        llm_provider: Optional[BaseLLMProvider] = None,
        settings: Optional[Settings] = None,
        max_retries: Optional[int] = None,
        force_fallback: bool = False,
    ):
        self.settings = settings or get_settings()
        self.retrieval_service = retrieval_service
        self.verification_service = verification_service
        self.llm_provider = llm_provider
        self.force_fallback = force_fallback
        self.max_retries = (
            max_retries
            if max_retries is not None
            else self.settings.max_verification_retries
        )

    def execute(
        self,
        request: DiagnosisRequest,
        investigation_id: str,
        initial_top_k: int = 5,
    ) -> Tuple[DiagnosticReport, EvidencePackage, VerificationRecord]:
        """Runs the complete self-verification loop.

        Returns:
            Tuple of (Finalized or Inconclusive DiagnosticReport, Final EvidencePackage, VerificationRecord)
        """
        history_steps: List[VerificationHistoryStep] = []
        attempted_query_signatures: Set[str] = set()
        seen_case_id_sets: List[Set[str]] = []

        current_symptoms = list(request.symptoms)
        current_top_k = initial_top_k
        current_subsystem = request.subsystem
        current_filter_mode = FilterMode.SOFT_RERANK

        retry_count = 0
        final_verdict = VerificationVerdict.INCONCLUSIVE.value
        final_status = "inconclusive_insufficient_evidence"
        report: Optional[DiagnosticReport] = None
        evidence_pkg: Optional[EvidencePackage] = None
        latest_verification: Optional[VerificationResult] = None

        while True:
            step_num = retry_count + 1
            query_signature = f"{'|'.join(sorted(current_symptoms))}::{request.fault_code or ''}::{current_subsystem}::{current_top_k}"
            logger.info("Executing verification loop step #%d (query signature: %s)", step_num, query_signature)

            # 1. Retrieve evidence
            evidence_pkg = self.retrieval_service.retrieve_evidence(
                symptoms=current_symptoms,
                fault_code=request.fault_code,
                subsystem=current_subsystem,
                telemetry=request.telemetry,
                top_k=current_top_k,
                filter_mode=current_filter_mode,
            )

            retrieved_ids = [it.case_id for it in evidence_pkg.items]
            retrieved_id_set = set(retrieved_ids)

            # Prevent futile repeated retrieval if query signature was already evaluated
            if query_signature in attempted_query_signatures:
                logger.info("Identical query signature previously executed; halting loop to prevent cycle.")
                break
            attempted_query_signatures.add(query_signature)

            # Check if retrieval yielded new cases compared to prior attempts
            if seen_case_id_sets and retrieved_id_set.issubset(seen_case_id_sets[-1]) and len(retrieved_id_set) > 0:
                logger.info("Expanded retrieval did not yield additional unique cases; knowledge base exhausted.")

            seen_case_id_sets.append(retrieved_id_set)

            # 2. Generate draft diagnosis (LLM reasoning or deterministic fallback)
            report = self._generate_draft_diagnosis(request, evidence_pkg, investigation_id, retry_count)

            # 3. Evidence verification check
            latest_verification = self.verification_service.verify(report, evidence_pkg, request)
            verdict = latest_verification.verdict
            logger.info(
                "Verification step #%d verdict: %s (Supported: %d, Partial: %d, Unsupported: %d, Contradicted: %d)",
                step_num,
                verdict,
                latest_verification.supported_count,
                latest_verification.partially_supported_count,
                latest_verification.unsupported_count,
                latest_verification.contradicted_count,
            )

            # 4. Check if sufficient evidence exists
            if latest_verification.is_verified and verdict == VerificationVerdict.SUFFICIENT.value:
                # Finalize diagnosis
                action_taken = "finalized"
                history_steps.append(
                    VerificationHistoryStep(
                        step_number=step_num,
                        retrieval_query=f"symptoms={current_symptoms}, fault={request.fault_code}, top_k={current_top_k}",
                        retrieved_case_ids=retrieved_ids,
                        draft_summary=report.summary,
                        draft_top_cause=report.top_candidate.hypothesis_title if report.top_candidate else None,
                        verdict=verdict,
                        supported_claims=latest_verification.supported_count,
                        unsupported_claims=latest_verification.unsupported_count,
                        contradicted_claims=latest_verification.contradicted_count,
                        reasons=["All major diagnostic claims verified against retrieved evidence."],
                        action_taken=action_taken,
                    )
                )
                final_verdict = VerificationVerdict.SUFFICIENT.value
                final_status = "verified_and_finalized"
                report.status = DiagnosticStatus.COMPLETED.value
                report.verification_verdict = final_verdict
                report.verification_details = latest_verification.to_dict()
                report.retry_count = retry_count
                break

            # If insufficient, contradicted, or inconclusive:
            # Check if retry limit reached
            if retry_count >= self.max_retries:
                action_taken = "max_retries_reached"
                reasons = list(latest_verification.missing_evidence_reasons)
                if not reasons:
                    reasons.append("Maximum verification retries exhausted without establishing sufficient evidence grounding.")

                history_steps.append(
                    VerificationHistoryStep(
                        step_number=step_num,
                        retrieval_query=f"symptoms={current_symptoms}, fault={request.fault_code}, top_k={current_top_k}",
                        retrieved_case_ids=retrieved_ids,
                        draft_summary=report.summary,
                        draft_top_cause=report.top_candidate.hypothesis_title if report.top_candidate else None,
                        verdict=verdict,
                        supported_claims=latest_verification.supported_count,
                        unsupported_claims=latest_verification.unsupported_count,
                        contradicted_claims=latest_verification.contradicted_count,
                        reasons=reasons,
                        action_taken=action_taken,
                    )
                )
                final_verdict = verdict
                final_status = "inconclusive_max_retries"
                report = self._build_inconclusive_report(
                    request=request,
                    evidence=evidence_pkg,
                    investigation_id=investigation_id,
                    verification_result=latest_verification,
                    retry_count=retry_count,
                    reason=f"Verification loop reached maximum retry limit ({self.max_retries}) without sufficient evidence grounding.",
                )
                break

            # Retries remain: Refine query / expand retrieval
            action_taken = "re_retrieval_initiated"
            reasons = list(latest_verification.missing_evidence_reasons)
            if latest_verification.suggested_query_refinements:
                reasons.append(f"Refinement suggestions: {'; '.join(latest_verification.suggested_query_refinements)}")

            history_steps.append(
                VerificationHistoryStep(
                    step_number=step_num,
                    retrieval_query=f"symptoms={current_symptoms}, fault={request.fault_code}, top_k={current_top_k}",
                    retrieved_case_ids=retrieved_ids,
                    draft_summary=report.summary,
                    draft_top_cause=report.top_candidate.hypothesis_title if report.top_candidate else None,
                    verdict=verdict,
                    supported_claims=latest_verification.supported_count,
                    unsupported_claims=latest_verification.unsupported_count,
                    contradicted_claims=latest_verification.contradicted_count,
                    reasons=reasons,
                    action_taken=action_taken,
                )
            )

            # Refinement Strategy:
            # 1. Expand top_k to retrieve more candidates
            current_top_k = min(current_top_k + 5, 20)

            # 2. Incorporate suggested refinement keywords into symptoms if available
            if latest_verification.suggested_query_refinements:
                for ref_kw in latest_verification.suggested_query_refinements[:2]:
                    clean_kw = ref_kw.strip().lower()
                    if clean_kw and clean_kw not in current_symptoms:
                        current_symptoms.append(clean_kw)

            # 3. If contradicted on subsystem, relax filter
            if latest_verification.contradicted_count > 0:
                current_filter_mode = FilterMode.SOFT_RERANK

            retry_count += 1

        # Construct full verification record
        verification_record = VerificationRecord(
            investigation_id=investigation_id,
            total_retries=retry_count,
            max_retries=self.max_retries,
            final_verdict=final_verdict,
            final_status=final_status,
            steps=history_steps,
        )

        return report, evidence_pkg, verification_record

    def _generate_draft_diagnosis(
        self,
        request: DiagnosisRequest,
        evidence: EvidencePackage,
        investigation_id: str,
        retry_count: int,
    ) -> DiagnosticReport:
        """Generates draft diagnosis via LLM or deterministic fallback."""
        if (
            self.llm_provider is not None
            and not self.force_fallback
            and evidence.items
        ):
            try:
                sys_prompt, user_prompt = DiagnosticPromptBuilder.build_prompts(request, evidence)
                # If this is a retry step, append instruction to address prior verification gaps
                if retry_count > 0:
                    user_prompt += (
                        f"\n\nNOTE (RETRY STEP {retry_count}): Ensure every single candidate cause is STRICTLY "
                        "grounded in the retrieved cases above. Do NOT formulate hypotheses that lack cited evidence."
                    )

                llm_resp = self.llm_provider.generate(
                    prompt=user_prompt,
                    system_prompt=sys_prompt,
                    temperature=self.settings.llm_temperature,
                    max_tokens=self.settings.llm_max_tokens,
                )
                draft = DiagnosticValidator.parse_and_validate(
                    llm_response=llm_resp,
                    request=request,
                    evidence=evidence,
                    investigation_id=investigation_id,
                )
                draft.retry_count = retry_count
                return draft
            except Exception as exc:
                logger.warning("Draft LLM diagnosis failed (%s); generating deterministic fallback draft.", exc)

        # Fallback draft
        draft = DeterministicFallbackEngine.generate_report(
            request=request,
            evidence=evidence,
            investigation_id=investigation_id,
            fallback_reason="Verification loop draft generation (offline or fallback).",
        )
        draft.retry_count = retry_count
        return draft

    def _build_inconclusive_report(
        self,
        request: DiagnosisRequest,
        evidence: EvidencePackage,
        investigation_id: str,
        verification_result: VerificationResult,
        retry_count: int,
        reason: str,
    ) -> DiagnosticReport:
        """Constructs an explicit INCONCLUSIVE report when verification criteria cannot be satisfied.

        Guarantees that an unsupported draft is NEVER silently approved as confirmed root cause.
        """
        missing_info = [
            f"Verification Failure Reason: {reason}",
            "Historical evidence in knowledge base was insufficient to corroborate observed elevator symptoms.",
        ]
        if verification_result.missing_evidence_reasons:
            missing_info.extend(verification_result.missing_evidence_reasons)

        recommended_checks = [
            f"Perform manual multimeter check across {request.subsystem} safety circuits and electrical contacts.",
            "Verify subsystem physical alignment, mechanical clearances, and wear surfaces.",
            "Inspect elevator controller event log buffer for cascading pre-trip faults.",
            "Consult OEM field engineering bulletins for uncataloged fault codes.",
        ]

        summary = (
            f"INCONCLUSIVE DIAGNOSTIC ASSESSMENT: The autonomous diagnostic system evaluated {len(evidence.items)} "
            f"retrieved historical cases, but after {retry_count} verification retries, evidence was insufficient "
            f"to substantiate candidate root causes with acceptable confidence. "
            f"Unsupported claims were rejected to prevent premature component replacement."
        )

        # Build conservative candidate causes clearly marked as unconfirmed hypotheses
        candid_causes: List[CandidateCause] = []
        for idx, item in enumerate(evidence.items[:2], start=1):
            candid_causes.append(
                CandidateCause(
                    rank=idx,
                    hypothesis_title=f"Unverified Reference: {item.confirmed_root_cause}",
                    subsystem=item.subsystem,
                    probability_band=ProbabilityBand.UNLIKELY.value,
                    explanation=(
                        f"Retrieved from historical case {item.case_id} ({item.source_title}), "
                        f"but flagged during verification as lacking complete corroboration with current symptoms."
                    ),
                    supporting_case_ids=[item.case_id],
                    recommended_checks=recommended_checks[:2],
                    documented_corrective_actions=[item.corrective_action],
                    citation_warnings=["Evidence sufficiency threshold not met during self-verification."],
                )
            )

        return DiagnosticReport(
            investigation_id=investigation_id,
            elevator_id=request.elevator_id,
            subsystem=request.subsystem,
            fault_code=request.fault_code,
            status=DiagnosticStatus.INCONCLUSIVE.value,
            summary=summary,
            candidate_causes=candid_causes,
            uncertainty_and_missing_info=missing_info,
            safety_advisories=[
                "MANDATORY: Lock-out / Tag-out (LOTO) power before opening controller or landing interlocks.",
                "DO NOT replace expensive drive modules or controllers without multimeter confirmation.",
            ],
            retrieved_case_ids=[it.case_id for it in evidence.items],
            generation_mode="verification_loop_inconclusive",
            model_metadata={"retry_count": retry_count, "verified_by": verification_result.verified_by},
            confidence_score=0.20,  # Explicit low confidence
            verification_verdict=verification_result.verdict,
            verification_details=verification_result.to_dict(),
            retry_count=retry_count,
        )
