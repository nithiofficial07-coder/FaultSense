"""Deterministic verification fallback engine for Phase 6.

Provides rule-based, reproducible claim grounding against retrieved evidence packages
in offline demo mode or when external LLM verification is unavailable.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Set

from src.diagnosis.schema import CandidateCause, DiagnosticReport
from src.diagnosis.session import DiagnosisRequest
from src.diagnosis.verification.schema import (
    ClaimStatus,
    ClaimVerification,
    VerificationResult,
    VerificationVerdict,
)
from src.retrieval.evidence import EvidenceItem, EvidencePackage, EvidenceSufficiencyLevel
from src.utils.logger import get_logger

logger = get_logger(__name__)

DETERMINISTIC_LIMITATIONS_NOTICE = (
    "Deterministic Verification Notice: Verified via rule-based heuristic evidence grounding "
    "(case ID provenance cross-checks, lexical token overlap, and subsystem bounds). "
    "This deterministic fallback cannot perform deep semantic natural-language entailment "
    "or multi-hop physical reasoning like an independent LLM verifier."
)


class DeterministicEvidenceVerifier:
    """Performs deterministic, rule-based verification of diagnostic claims against evidence."""

    @classmethod
    def verify(
        cls,
        report: DiagnosticReport,
        evidence: EvidencePackage,
        request: DiagnosisRequest,
    ) -> VerificationResult:
        """Verifies diagnostic report claims against retrieved evidence items."""
        claims: List[ClaimVerification] = []
        supported_count = 0
        partially_supported_count = 0
        unsupported_count = 0
        contradicted_count = 0
        missing_reasons: List[str] = []
        suggested_refinements: List[str] = []

        # Map retrieved evidence by case_id for quick lookup
        evidence_by_id: Dict[str, EvidenceItem] = {
            item.case_id: item for item in evidence.items
        }
        retrieved_ids: Set[str] = set(evidence_by_id.keys())

        # If knowledge base returned zero cases
        if not evidence.items:
            verdict = VerificationVerdict.INCONCLUSIVE.value
            missing_reasons.append("Retrieved evidence package is empty; no historical cases available to verify claims.")
            suggested_refinements.append("Broaden symptom query keywords or remove exact fault code constraint.")
            return VerificationResult(
                verdict=verdict,
                is_verified=False,
                verified_by="deterministic_evidence_verifier",
                claims=[],
                supported_count=0,
                partially_supported_count=0,
                unsupported_count=len(report.candidate_causes),
                contradicted_count=0,
                missing_evidence_reasons=missing_reasons,
                suggested_query_refinements=suggested_refinements,
                is_fallback=True,
                limitations_notice=DETERMINISTIC_LIMITATIONS_NOTICE,
                notes="Zero evidence retrieved; cannot verify diagnostic draft.",
            )

        # Inspect each candidate cause as a major diagnostic claim
        for candidate in report.candidate_causes:
            claim_text = f"{candidate.hypothesis_title}: {candidate.explanation}"
            cited_ids = candidate.supporting_case_ids
            grounding_texts: List[str] = []
            contradictions: List[str] = []
            claim_status = ClaimStatus.UNSUPPORTED.value

            # Check 1: Are citations present and do they exist in the evidence package?
            valid_cited_items = [evidence_by_id[cid] for cid in cited_ids if cid in evidence_by_id]
            invalid_citations = [cid for cid in cited_ids if cid not in evidence_by_id]

            if invalid_citations:
                contradictions.append(
                    f"Candidate cites case ID(s) {invalid_citations} that do NOT exist in the retrieved evidence."
                )

            # Check 2: Contradiction with physical request / evidence signals
            # e.g., candidate subsystem contradicts query subsystem when not physically coupled
            if candidate.subsystem and request.subsystem:
                cand_sub = candidate.subsystem.strip().lower().replace("-", "_")
                req_sub = request.subsystem.strip().lower().replace("-", "_")
                if cand_sub != req_sub:
                    # Check if evidence mentions candidate's subsystem
                    subsystem_in_evidence = any(
                        cand_sub == it.subsystem.strip().lower().replace("-", "_")
                        for it in evidence.items
                    )
                    if not subsystem_in_evidence:
                        contradictions.append(
                            f"Hypothesis targets subsystem '{candidate.subsystem}' which is neither the requested "
                            f"subsystem ('{request.subsystem}') nor supported by any retrieved evidence item."
                        )

            # Check 2b: Telemetry physical contradiction
            # e.g., telemetry measures current flow but hypothesis asserts open-circuit coil
            if request.telemetry:
                tel_str = json.dumps(request.telemetry).lower()
                claim_lower = claim_text.lower()
                has_current = any(
                    k in tel_str and isinstance(v, (int, float)) and v > 0.5
                    for k, v in request.telemetry.items()
                    if "current" in k.lower()
                )
                if has_current and ("open-circuit" in claim_lower or "open coil" in claim_lower):
                    contradictions.append(
                        "Measured sensor current directly contradicts open-circuit coil hypothesis."
                    )

            # Check 3: Grounding against valid cited items or overall evidence
            target_evidence_items = valid_cited_items if valid_cited_items else evidence.items
            best_overlap_ratio = 0.0
            best_symptom_overlap = 0.0
            best_match_text = ""

            # Extract specific inquiry symptom keywords
            req_words = set(re.findall(r"\w{4,}", " ".join(request.symptoms).lower()))
            generic_stop = {"elevator", "during", "travel", "doors", "stops", "transit", "switch", "status", "reported", "check"}
            specific_req = req_words - generic_stop

            for it in target_evidence_items:
                evidence_text = f"{it.confirmed_root_cause} {it.corrective_action} {' '.join(it.symptoms)}".lower()
                claim_words = set(re.findall(r"\w{4,}", claim_text.lower()))
                evidence_words = set(re.findall(r"\w{4,}", evidence_text))

                if not claim_words:
                    overlap = 0.0
                else:
                    overlap = len(claim_words.intersection(evidence_words)) / len(claim_words)

                if specific_req:
                    sym_overlap = len(specific_req.intersection(evidence_words)) / len(specific_req)
                else:
                    sym_overlap = 1.0

                if sym_overlap > best_symptom_overlap:
                    best_symptom_overlap = sym_overlap

                if overlap > best_overlap_ratio:
                    best_overlap_ratio = overlap
                    best_match_text = f"Case {it.case_id}: {it.confirmed_root_cause}"

            # Classify claim status based on overlap, citations, and symptom alignment
            if contradictions:
                claim_status = ClaimStatus.CONTRADICTED.value
                contradicted_count += 1
            elif valid_cited_items and best_overlap_ratio >= 0.25 and best_symptom_overlap >= 0.20:
                claim_status = ClaimStatus.SUPPORTED.value
                supported_count += 1
                grounding_texts.append(f"Grounded by {', '.join([it.case_id for it in valid_cited_items])}: {best_match_text}")
            elif best_overlap_ratio >= 0.15 and best_symptom_overlap >= 0.15:
                claim_status = ClaimStatus.PARTIALLY_SUPPORTED.value
                partially_supported_count += 1
                grounding_texts.append(f"Partial lexical overlap ({int(best_overlap_ratio*100)}%) with {best_match_text}")
            else:
                claim_status = ClaimStatus.UNSUPPORTED.value
                unsupported_count += 1
                if best_symptom_overlap < 0.20:
                    missing_reasons.append(
                        f"Retrieved case {best_match_text[:30]} does not match reported symptoms (symptom alignment: {int(best_symptom_overlap*100)}%)."
                    )
                else:
                    missing_reasons.append(
                        f"Claim '{candidate.hypothesis_title}' lacks textual grounding in retrieved cases."
                    )

            claims.append(
                ClaimVerification(
                    claim_text=claim_text,
                    status=claim_status,
                    cited_case_ids=cited_ids,
                    grounding_evidence=grounding_texts,
                    contradictions=contradictions,
                    missing_evidence_notes=f"Overlap ratio: {round(best_overlap_ratio, 2)}"
                    if claim_status != ClaimStatus.SUPPORTED.value
                    else "",
                )
            )

        # Check evidence sufficiency floor
        if evidence.sufficiency.level == EvidenceSufficiencyLevel.INSUFFICIENT.value:
            suff_reasons = "; ".join(evidence.sufficiency.reasons) if getattr(evidence.sufficiency, "reasons", None) else "low similarity"
            missing_reasons.append(
                f"Evidence package sufficiency is marked INSUFFICIENT ({suff_reasons})."
            )

        # Formulate aggregate verdict based on primary root cause claim
        primary_status = claims[0].status if claims else ClaimStatus.UNSUPPORTED.value

        if contradicted_count > 0:
            verdict = VerificationVerdict.CONTRADICTED.value
            is_verified = False
        elif primary_status == ClaimStatus.SUPPORTED.value and evidence.sufficiency.level != EvidenceSufficiencyLevel.INSUFFICIENT.value:
            verdict = VerificationVerdict.SUFFICIENT.value
            is_verified = True
        elif primary_status == ClaimStatus.PARTIALLY_SUPPORTED.value:
            verdict = VerificationVerdict.INSUFFICIENT.value
            is_verified = False
            suggested_refinements.append("Include related subsystem keywords or expand search top_k.")
        else:
            verdict = VerificationVerdict.INSUFFICIENT.value
            is_verified = False
            suggested_refinements.append("Retrieve additional cases with expanded query terms.")

        return VerificationResult(
            verdict=verdict,
            is_verified=is_verified,
            verified_by="deterministic_evidence_verifier",
            claims=claims,
            supported_count=supported_count,
            partially_supported_count=partially_supported_count,
            unsupported_count=unsupported_count,
            contradicted_count=contradicted_count,
            missing_evidence_reasons=missing_reasons,
            suggested_query_refinements=suggested_refinements,
            is_fallback=True,
            limitations_notice=DETERMINISTIC_LIMITATIONS_NOTICE,
            notes=f"Deterministic verification completed with verdict: {verdict}",
        )
