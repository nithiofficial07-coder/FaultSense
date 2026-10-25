"""Technician Decision-Support Diagnosis Engine for FaultSense.

Coordinates technician symptom input, knowledge retrieval, LLM action synthesis,
and Phase 6 Agentic Self-Verification loop with deterministic fallbacks.
"""

from __future__ import annotations

import time
import uuid
from typing import Optional

from config.settings import get_settings
from src.diagnosis.evidence_scorer import EvidenceScorer
from src.diagnosis.fallback import DeterministicFallbackEngine
from src.diagnosis.llm import BaseLLMProvider, get_llm_provider
from src.diagnosis.prompt_builder import DiagnosticPromptBuilder
from src.diagnosis.schema import DiagnosticReport, DiagnosticStatus
from src.diagnosis.session import DiagnosisRequest, DiagnosisResult
from src.diagnosis.validator import DiagnosticValidator
from src.diagnosis.verification import (
    AgenticVerificationLoop,
    DiagnosisVerificationService,
    VerificationRecord,
)
from src.retrieval.evidence import EvidencePackage, EvidenceSufficiencyLevel
from src.retrieval.retrieval_service import FaultRetrievalService
from src.retrieval.retriever import BaseRetriever, HybridRetriever
from src.storage.repository import InvestigationRepository
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DiagnosisEngine:
    """Coordinates technician symptom input, knowledge retrieval, LLM reasoning, and self-verification."""

    def __init__(
        self,
        retriever: Optional[BaseRetriever] = None,
        retrieval_service: Optional[FaultRetrievalService] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
        verification_service: Optional[DiagnosisVerificationService] = None,
        investigation_repo: Optional[InvestigationRepository] = None,
        force_fallback: bool = False,
        enable_verification: Optional[bool] = None,
        max_verification_retries: Optional[int] = None,
    ):
        self.settings = get_settings()
        self.retrieval_service = retrieval_service
        self.retriever = retriever
        self.force_fallback = force_fallback
        self.enable_verification = (
            enable_verification
            if enable_verification is not None
            else self.settings.verification_enabled
        )
        self.max_verification_retries = (
            max_verification_retries
            if max_verification_retries is not None
            else self.settings.max_verification_retries
        )

        # Initialize retrieval service if not passed
        if self.retrieval_service is None and self.retriever is None:
            try:
                self.retrieval_service = FaultRetrievalService()
            except Exception as exc:
                logger.warning("Could not initialize FaultRetrievalService (%s); falling back to HybridRetriever.", exc)
                self.retriever = HybridRetriever()

        # Initialize LLM provider unless forced into fallback or demo mode
        self.llm_provider = llm_provider
        if self.llm_provider is None and not self.force_fallback and not self.settings.is_demo_mode:
            try:
                self.llm_provider = get_llm_provider(self.settings)
            except Exception as exc:
                logger.warning("Could not initialize LLM provider (%s); operating in fallback mode.", exc)
                self.llm_provider = None

        # Initialize independent verification service (Requirement 1)
        self.verification_service = verification_service or DiagnosisVerificationService(
            llm_provider=None,
            settings=self.settings,
            force_fallback=self.force_fallback,
        )

        self.investigation_repo = investigation_repo or InvestigationRepository()

    def analyze(self, request: DiagnosisRequest) -> DiagnosisResult:
        """Analyzes reported symptoms and telemetry through the agentic self-verification loop."""
        logger.info(
            "Analyzing elevator '%s' subsystem '%s' (fault code: %s)",
            request.elevator_id,
            request.subsystem,
            request.fault_code or "None",
        )

        inv_id = f"INV-{int(time.time())}-{uuid.uuid4().hex[:6]}"
        matched: list = []
        evidence_dict: Optional[dict] = None
        report: Optional[DiagnosticReport] = None
        verification_record: Optional[VerificationRecord] = None
        sufficiency_level: str = "moderate"
        warnings: list = []
        is_ai_generated = False
        mode_notice = ""
        generation_mode = "fallback_deterministic"
        is_verified = False
        retry_count = 0

        # Phase 6: Execute Agentic Self-Verification Loop if retrieval service is available
        if self.retrieval_service is not None and self.enable_verification:
            loop = AgenticVerificationLoop(
                retrieval_service=self.retrieval_service,
                verification_service=self.verification_service,
                llm_provider=self.llm_provider,
                settings=self.settings,
                max_retries=self.max_verification_retries,
                force_fallback=self.force_fallback,
            )
            report, evidence_pkg, verification_record = loop.execute(
                request=request,
                investigation_id=inv_id,
                initial_top_k=self.settings.top_k_retrieval,
            )

            evidence_dict = evidence_pkg.to_dict()
            sufficiency_level = evidence_pkg.sufficiency.level
            warnings = list(evidence_pkg.warnings)
            matched = [it.to_dict() for it in evidence_pkg.items]
            generation_mode = report.generation_mode
            retry_count = verification_record.total_retries
            is_verified = verification_record.final_status == "verified_and_finalized"

            if "llm" in generation_mode.lower():
                is_ai_generated = True

            if is_verified:
                mode_notice = f"Phase 6 Self-Verified ({generation_mode}) - Verdict: SUFFICIENT (Retries: {retry_count})"
            else:
                mode_notice = f"Phase 6 Inconclusive ({report.verification_verdict or 'insufficient'}) - {verification_record.final_status}"

        elif self.retrieval_service is not None:
            # Direct retrieval without verification loop
            evidence_pkg = self.retrieval_service.retrieve_evidence(
                symptoms=request.symptoms,
                fault_code=request.fault_code,
                subsystem=request.subsystem,
                telemetry=request.telemetry,
                top_k=self.settings.top_k_retrieval,
            )
            evidence_dict = evidence_pkg.to_dict()
            sufficiency_level = evidence_pkg.sufficiency.level
            warnings = list(evidence_pkg.warnings)
            matched = [it.to_dict() for it in evidence_pkg.items]

            if self.llm_provider is not None and not self.force_fallback:
                try:
                    sys_prompt, user_prompt = DiagnosticPromptBuilder.build_prompts(request, evidence_pkg)
                    llm_resp = self.llm_provider.generate(
                        prompt=user_prompt,
                        system_prompt=sys_prompt,
                        temperature=self.settings.llm_temperature,
                        max_tokens=self.settings.llm_max_tokens,
                    )
                    report = DiagnosticValidator.parse_and_validate(
                        llm_response=llm_resp,
                        request=request,
                        evidence=evidence_pkg,
                        investigation_id=inv_id,
                    )
                    is_ai_generated = True
                    generation_mode = "llm_reasoning"
                    mode_notice = f"Phase 5 LLM Reasoning ({llm_resp.provider} / {llm_resp.model})"
                    logger.info("Successfully generated LLM diagnostic report via %s (%s)", llm_resp.provider, llm_resp.model)
                except Exception as exc:
                    logger.warning("LLM diagnostic generation failed (%s); engaging deterministic fallback.", exc)
                    warnings.append(f"LLM Reasoning unavailable ({type(exc).__name__}); generated via deterministic historical fallback.")
                    report = DeterministicFallbackEngine.generate_report(
                        request=request,
                        evidence=evidence_pkg,
                        investigation_id=inv_id,
                        fallback_reason=f"LLM exception: {exc}",
                    )
                    is_ai_generated = False
                    generation_mode = "fallback_deterministic"
                    mode_notice = f"Phase 5 Deterministic Fallback Notice: LLM API error ({type(exc).__name__}). Using historical evidence mapping."
            else:
                report = DeterministicFallbackEngine.generate_report(
                    request=request,
                    evidence=evidence_pkg,
                    investigation_id=inv_id,
                    fallback_reason="Offline demo mode: No external LLM API key configured.",
                )
                is_ai_generated = False
                generation_mode = "fallback_deterministic"
                mode_notice = "Phase 5 Deterministic Historical Fallback (Demo / Offline Mode). No LLM API invoked."
        else:
            # Legacy fallback if retrieval service is completely absent
            search_query = f"{request.fault_code or ''} {' '.join(request.symptoms)}".strip()
            matched = self.retriever.retrieve(
                query=search_query,
                top_k=self.settings.top_k_retrieval,
                subsystem=request.subsystem,
            ) if self.retriever else []
            root_cause = (
                matched[0]["confirmed_root_cause"]
                if matched
                else f"Physical diagnostic isolation required for subsystem '{request.subsystem}'."
            )
            corrective = [matched[0]["corrective_action"]] if matched else ["Inspect subsystem assembly."]
            confidence = matched[0]["score"] if matched else 0.40
            mode_notice = "Phase 1 Heuristic Baseline (Legacy)"

        # Extract top findings from report if built
        if report is not None:
            top_cause = report.top_candidate
            if top_cause and report.status != DiagnosticStatus.INCONCLUSIVE.value:
                root_cause = top_cause.hypothesis_title
                corrective = list(top_cause.documented_corrective_actions)
                if top_cause.recommended_checks:
                    corrective.extend(top_cause.recommended_checks[:2])
            else:
                root_cause = report.summary
                corrective = [
                    f"Perform manual multimeter check across {request.subsystem} electrical circuits.",
                    "Verify physical mechanical clearances and sensor alignment.",
                ]
            confidence = report.confidence_score

        # Identify any physical contradictions or verification failures
        contradictions_found: list = []
        if verification_record and hasattr(verification_record, "steps"):
            for step in verification_record.steps:
                if getattr(step, "contradicted_claims", 0) > 0:
                    contradictions_found.extend(getattr(step, "reasons", []))

        verdict_str = report.verification_verdict if (report and getattr(report, "verification_verdict", None)) else ("sufficient" if is_verified else "unverified")
        verif_failed = bool(verification_record and "fail" in getattr(verification_record, "final_status", "").lower())

        # Calculate empirical evidence support score
        evidence_items_list = evidence_pkg.items if ('evidence_pkg' in locals() and evidence_pkg is not None) else []
        calculated_conf, breakdown = EvidenceScorer.compute_confidence(
            evidence_items=evidence_items_list,
            request_symptoms=request.symptoms,
            request_fault_code=request.fault_code,
            request_subsystem=request.subsystem,
            request_telemetry=request.telemetry,
            verification_verdict=verdict_str,
            is_verified=is_verified,
            contradictions=contradictions_found,
            verification_failed=verif_failed,
        )

        status_type = EvidenceScorer.determine_status(
            is_verified=is_verified,
            verification_verdict=verdict_str,
            confidence_score=calculated_conf,
            evidence_items=evidence_items_list,
            has_fault_code=bool(request.fault_code and request.fault_code.strip()),
            has_telemetry=bool(request.telemetry and len(request.telemetry) > 0),
            symptom_count=len(request.symptoms),
            contradictions=contradictions_found,
            verification_failed=verif_failed,
        )
        diagnostic_status = status_type.value
        confidence = calculated_conf

        if report is not None:
            report.confidence_score = confidence
            if hasattr(report, "model_metadata") and isinstance(report.model_metadata, dict):
                report.model_metadata["confidence_breakdown"] = breakdown.to_dict()

        result = DiagnosisResult(
            investigation_id=inv_id,
            elevator_id=request.elevator_id,
            subsystem=request.subsystem,
            root_cause_hypothesis=root_cause,
            confidence_score=round(confidence, 2),
            recommended_actions=corrective,
            matched_cases=matched,
            is_ai_generated=is_ai_generated,
            mode_notice=mode_notice,
            evidence_package=evidence_dict,
            diagnostic_report=report.to_dict() if report else None,
            generation_mode=generation_mode,
            sufficiency_level=sufficiency_level,
            warnings=warnings,
            verification_record=verification_record.to_dict() if verification_record else None,
            retry_count=retry_count,
            is_verified=is_verified,
            diagnostic_status=diagnostic_status,
            confidence_breakdown=breakdown.to_dict(),
        )

        # Persist session to SQLite
        try:
            self.investigation_repo.create({
                "investigation_id": inv_id,
                "elevator_id": request.elevator_id,
                "building_id": request.building_id,
                "subsystem": request.subsystem,
                "fault_code": request.fault_code,
                "symptoms": request.symptoms,
                "telemetry": request.telemetry,
                "root_cause_hypothesis": root_cause,
                "recommended_actions": "\n".join(corrective),
                "confidence_score": confidence,
                "matched_case_ids": [m["case_id"] for m in matched],
                "status": "completed" if is_verified else "inconclusive",
                "diagnostic_status": diagnostic_status,
                "confidence_breakdown": breakdown.to_dict(),
                "technician_notes": request.technician_notes,
                "verification_record": verification_record.to_dict() if verification_record else None,
                "retry_count": retry_count,
                "diagnostic_report": report.to_dict() if report else None,
                "evidence_package": evidence_dict,
                "manufacturer": getattr(request, "manufacturer", None) or "Not Specified",
                "equipment_model": getattr(request, "equipment_model", None) or "Not Specified",
                "problem_description": getattr(request, "problem_description", None) or (request.symptoms[0] if request.symptoms else "Reported elevator operational malfunction"),
                "operating_conditions": getattr(request, "operating_conditions", None) or "Standard Duty Cycle",
                "severity": getattr(request, "severity", None) or "Medium",
            })
        except Exception as exc:
            logger.warning("Could not persist investigation session: %s", exc)

        return result
