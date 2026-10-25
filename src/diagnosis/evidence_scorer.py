"""Evidence-Grounded Confidence Scoring and Diagnostic Status Evaluator for FaultSense.

Provides a fully transparent, testable, and deterministic mathematical scoring
framework for evaluating diagnostic confidence based on measurable empirical factors:
1. Retrieval semantic and composite relevance.
2. Exact diagnostic trouble code (DTC) alignment.
3. Lexical symptom keyword overlap between technician report and retrieved cases.
4. Physical sensor telemetry completeness and absence of sensor contradictions.
5. Corroboration across multiple distinct historical cases.
6. Verification loop execution outcome and claim audit verdict.

Strictly adheres to decision-support safety principles:
- Fixed confidence constants (e.g. 88%, 85%) are strictly prohibited.
- Missing evidence reduces certainty or yields an explicit INSUFFICIENT EVIDENCE status.
- Contradictory evidence triggers CONFLICTING EVIDENCE and caps confidence below 0.25.
- Zero-evidence retrieval yields an explicit INSUFFICIENT EVIDENCE status with score <= 0.15.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


class DiagnosticStatusType(str, Enum):
    """Explicit, evidence-driven diagnostic statuses supported by FaultSense."""
    AWAITING_ANALYSIS = "Awaiting Analysis"
    ANALYSIS_COMPLETED = "Analysis Completed"
    EVIDENCE_SUPPORTED = "Evidence Supported"
    PARTIALLY_SUPPORTED = "Partially Supported"
    CONFLICTING_EVIDENCE = "Conflicting Evidence"
    INSUFFICIENT_EVIDENCE = "Insufficient Evidence"
    VERIFICATION_FAILED = "Verification Failed"
    REVIEW_REQUIRED = "Review Required"


@dataclass
class ConfidenceBreakdown:
    """Documented breakdown of factors contributing to the Evidence Support Score."""
    semantic_similarity: float
    semantic_component: float
    exact_fault_code_match: bool
    fault_code_component: float
    symptom_overlap_ratio: float
    symptom_component: float
    telemetry_provided: bool
    telemetry_component: float
    corroboration_count: int
    corroboration_component: float
    penalties_applied: List[str]
    raw_total: float
    bounded_score: float
    verification_verdict: str
    scoring_notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EvidenceScorer:
    """Evaluates dynamic evidence support scores and assigns evidence-driven diagnostic statuses."""

    # Standard stop words excluded from symptom overlap evaluation
    STOP_WORDS: Set[str] = {
        "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with", "by",
        "of", "is", "was", "are", "were", "be", "been", "has", "have", "had", "car",
        "elevator", "observed", "reported", "status", "during", "travel", "doors",
    }

    @classmethod
    def extract_keywords(cls, texts: Sequence[str]) -> Set[str]:
        """Extracts normalized keywords (length >= 3) excluding generic stop words."""
        joined = " ".join(texts).lower()
        words = re.findall(r"[a-z0-9_-]{3,}", joined)
        return set(words) - cls.STOP_WORDS

    @classmethod
    def compute_symptom_overlap(
        cls,
        input_symptoms: Sequence[str],
        case_symptoms: Sequence[str],
        case_root_cause: str = "",
    ) -> float:
        """Computes lexical token overlap ratio between reported symptoms and historical case."""
        in_words = cls.extract_keywords(input_symptoms)
        if not in_words:
            return 0.0

        case_texts = list(case_symptoms)
        if case_root_cause:
            case_texts.append(case_root_cause)
        case_words = cls.extract_keywords(case_texts)

        if not case_words:
            return 0.0

        intersection = in_words.intersection(case_words)
        return round(len(intersection) / len(in_words), 4)

    @classmethod
    def compute_confidence(
        cls,
        evidence_items: Sequence[Any],
        request_symptoms: Sequence[str],
        request_fault_code: Optional[str] = None,
        request_subsystem: Optional[str] = None,
        request_telemetry: Optional[Dict[str, Any]] = None,
        verification_verdict: Optional[str] = None,
        is_verified: bool = False,
        contradictions: Optional[Sequence[str]] = None,
        verification_failed: bool = False,
    ) -> Tuple[float, ConfidenceBreakdown]:
        """Calculates an empirical Evidence Support Score bounded in [0.05, 0.98].

        Mathematical Model:
            Raw Score = w_sim * S_sim + w_dtc * S_dtc + w_sym * S_sym + w_tel * S_tel + w_cor * S_cor
            Subject to verification bounds and contradiction penalties:
            - Contradictions present -> Capped at <= 0.25
            - Insufficient evidence / 0 cases -> Capped at <= 0.15
            - Partially supported -> Capped at <= 0.58
            - Verified sufficient -> Bounded in [0.60, 0.96]
        """
        penalties: List[str] = []
        contradictions_list = list(contradictions or [])

        # Case 1: Zero evidence cases retrieved
        if not evidence_items:
            breakdown = ConfidenceBreakdown(
                semantic_similarity=0.0,
                semantic_component=0.0,
                exact_fault_code_match=False,
                fault_code_component=0.0,
                symptom_overlap_ratio=0.0,
                symptom_component=0.0,
                telemetry_provided=bool(request_telemetry),
                telemetry_component=0.0,
                corroboration_count=0,
                corroboration_component=0.0,
                penalties_applied=["Zero historical records matched query or filter constraints."],
                raw_total=0.08,
                bounded_score=0.10,
                verification_verdict=verification_verdict or "insufficient",
                scoring_notes="Insufficient evidence: Knowledge base contains no close precedents.",
            )
            return 0.10, breakdown

        # Top evidence item metrics
        top_item = evidence_items[0]
        top_sim = float(getattr(top_item, "similarity_score", 0.0) or (top_item.get("similarity_score", 0.0) if isinstance(top_item, dict) else 0.0))
        top_composite = float(getattr(top_item, "composite_score", top_sim) or (top_item.get("composite_score", top_sim) if isinstance(top_item, dict) else top_sim))
        top_case_code = getattr(top_item, "fault_code", None) or (top_item.get("fault_code") if isinstance(top_item, dict) else None)
        top_case_sub = getattr(top_item, "subsystem", None) or (top_item.get("subsystem") if isinstance(top_item, dict) else None)
        top_case_syms = getattr(top_item, "symptoms", []) or (top_item.get("symptoms", []) if isinstance(top_item, dict) else [])
        top_case_cause = getattr(top_item, "confirmed_root_cause", "") or (top_item.get("confirmed_root_cause", "") if isinstance(top_item, dict) else "")

        # 1. Semantic Relevance Component (Weight: 0.35)
        # Cosine similarity for all-MiniLM-L6-v2 typically ranges [0.25, 0.85] for relevant items
        norm_sim = max(0.0, min(1.0, (top_sim - 0.20) / 0.70)) if top_sim > 0.20 else 0.0
        semantic_comp = round(norm_sim * 0.35, 4)

        # 2. Exact Fault Code Alignment (Weight: 0.18)
        clean_req_code = request_fault_code.strip().upper() if request_fault_code else ""
        clean_case_code = top_case_code.strip().upper() if top_case_code else ""
        has_exact_dtc = bool(clean_req_code and clean_case_code and clean_req_code == clean_case_code)

        if has_exact_dtc:
            dtc_comp = 0.18
        elif any(
            clean_req_code and getattr(it, "fault_code", "").strip().upper() == clean_req_code
            for it in evidence_items[1:]
        ):
            dtc_comp = 0.10  # Secondary match
            penalties.append("Exact DTC code matched in secondary evidence item rather than top rank.")
        elif not clean_req_code:
            dtc_comp = 0.00
            penalties.append("No OEM diagnostic trouble code provided (-18% DTC weight unearned).")
        else:
            dtc_comp = 0.00
            penalties.append(f"OEM trouble code '{clean_req_code}' does not match top precedent '{clean_case_code}'.")

        # 3. Symptom Lexical Overlap Component (Weight: 0.22)
        symptom_overlap = cls.compute_symptom_overlap(request_symptoms, top_case_syms, top_case_cause)
        symptom_comp = round(min(1.0, symptom_overlap * 1.25) * 0.22, 4)
        if symptom_overlap < 0.20:
            penalties.append(f"Low symptom alignment with top precedent ({int(symptom_overlap * 100)}% overlap).")

        # 4. Telemetry Completeness & Consistency Component (Weight: 0.15)
        has_telemetry = bool(request_telemetry and isinstance(request_telemetry, dict) and len(request_telemetry) > 0)
        has_contradictions = bool(contradictions_list)

        if has_contradictions:
            telemetry_comp = -0.30
            penalties.append(f"PHYSICAL CONTRADICTION: {'; '.join(contradictions_list[:2])}")
        elif has_telemetry:
            # Check numerical readings present
            numeric_count = sum(1 for v in request_telemetry.values() if isinstance(v, (int, float)))
            if numeric_count >= 2:
                telemetry_comp = 0.15
            elif numeric_count == 1:
                telemetry_comp = 0.10
                penalties.append("Only single sensor telemetry parameter supplied.")
            else:
                telemetry_comp = 0.05
        else:
            telemetry_comp = 0.00
            penalties.append("Sensor telemetry omitted; physical operating margins could not be cross-validated.")

        # 5. Corroboration Across Precedents (Weight: 0.10)
        corroboration_count = 1
        clean_req_sub = request_subsystem.strip().lower() if request_subsystem else ""
        for other in evidence_items[1:]:
            other_sub = str(getattr(other, "subsystem", "") or other.get("subsystem", "")).strip().lower()
            other_sim = float(getattr(other, "similarity_score", 0.0) or (other.get("similarity_score", 0.0) if isinstance(other, dict) else 0.0))
            if other_sub == clean_req_sub and other_sim >= 0.40:
                corroboration_count += 1

        if corroboration_count >= 3:
            corroboration_comp = 0.10
        elif corroboration_count == 2:
            corroboration_comp = 0.06
        else:
            corroboration_comp = 0.02
            penalties.append("Isolated precedent; limited multi-case corroboration in knowledge base.")

        # Aggregate raw score
        raw_total = semantic_comp + dtc_comp + symptom_comp + telemetry_comp + corroboration_comp

        # 6. Verification Loop Bounds & Overrides
        verdict_str = (verification_verdict or "").strip().lower()

        if has_contradictions or verdict_str == "contradicted":
            bounded = max(0.08, min(raw_total, 0.25))
            scoring_notes = "Confidence capped below 25% due to direct physical contradictions between telemetry and claims."
        elif verification_failed:
            bounded = max(0.10, min(raw_total, 0.35))
            scoring_notes = "Confidence capped below 35% because diagnostic verification failed to validate claims."
        elif verdict_str == "insufficient":
            bounded = max(0.12, min(raw_total, 0.38))
            scoring_notes = "Confidence capped below 38%: verification loop determined evidence is insufficient."
        elif verdict_str == "partially_supported":
            bounded = max(0.25, min(raw_total, 0.58))
            scoring_notes = "Moderate confidence: claims are partially grounded but lack complete verification."
        elif is_verified or verdict_str == "sufficient":
            # Baseline boost for verified evidence grounding
            verified_score = max(raw_total, 0.62)
            bounded = min(0.96, verified_score)
            scoring_notes = "High confidence: primary claims verified against documented historical records and sensor limits."
        else:
            bounded = max(0.15, min(0.85, raw_total))
            scoring_notes = "Preliminary advisory support score based on unverified heuristic matching."

        final_score = round(max(0.05, min(0.98, bounded)), 2)

        breakdown = ConfidenceBreakdown(
            semantic_similarity=round(top_sim, 4),
            semantic_component=semantic_comp,
            exact_fault_code_match=has_exact_dtc,
            fault_code_component=dtc_comp,
            symptom_overlap_ratio=symptom_overlap,
            symptom_component=symptom_comp,
            telemetry_provided=has_telemetry,
            telemetry_component=telemetry_comp,
            corroboration_count=corroboration_count,
            corroboration_component=corroboration_comp,
            penalties_applied=penalties,
            raw_total=round(raw_total, 4),
            bounded_score=final_score,
            verification_verdict=verification_verdict or ("sufficient" if is_verified else "unverified"),
            scoring_notes=scoring_notes,
        )

        return final_score, breakdown

    @classmethod
    def determine_status(
        cls,
        is_verified: bool,
        verification_verdict: Optional[str],
        confidence_score: float,
        evidence_items: Sequence[Any],
        has_fault_code: bool,
        has_telemetry: bool,
        symptom_count: int,
        contradictions: Optional[Sequence[str]] = None,
        verification_failed: bool = False,
    ) -> DiagnosticStatusType:
        """Determines explicit, evidence-driven diagnostic status based on measurable criteria.

        Transition Rules:
        1. Contradictions exist -> CONFLICTING_EVIDENCE
        2. Verification service failed -> VERIFICATION_FAILED
        3. 0 evidence items or confidence <= 0.30 -> INSUFFICIENT_EVIDENCE
        4. is_verified AND verdict == 'sufficient' AND confidence >= 0.60:
             If has_fault_code and has_telemetry -> EVIDENCE_SUPPORTED
             Else -> REVIEW_REQUIRED (grounded hypothesis, but missing on-site multimeter proof)
        5. verdict == 'partially_supported' or confidence in [0.35, 0.59] -> PARTIALLY_SUPPORTED
        6. Default -> REVIEW_REQUIRED
        """
        contradictions_list = list(contradictions or [])
        verdict_clean = (verification_verdict or "").strip().lower()

        if contradictions_list or verdict_clean == "contradicted":
            return DiagnosticStatusType.CONFLICTING_EVIDENCE

        if verification_failed:
            return DiagnosticStatusType.VERIFICATION_FAILED

        if not evidence_items or len(evidence_items) == 0 or confidence_score <= 0.30 or verdict_clean == "insufficient":
            return DiagnosticStatusType.INSUFFICIENT_EVIDENCE

        if (is_verified or verdict_clean == "sufficient") and confidence_score >= 0.60:
            if has_fault_code and has_telemetry:
                return DiagnosticStatusType.EVIDENCE_SUPPORTED
            else:
                # Fully grounded hypothesis, but requires technician field verification of missing signals
                return DiagnosticStatusType.REVIEW_REQUIRED

        if verdict_clean == "partially_supported" or (0.35 <= confidence_score < 0.60):
            return DiagnosticStatusType.PARTIALLY_SUPPORTED

        return DiagnosticStatusType.REVIEW_REQUIRED


__all__ = [
    "ConfidenceBreakdown",
    "DiagnosticStatusType",
    "EvidenceScorer",
]
