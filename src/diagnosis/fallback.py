"""Deterministic fallback reasoning engine for offline, demo, and API-outage modes.

Generates structured diagnostic reports directly from retrieved FAISS historical cases
without invoking an LLM. Transparently labels fallback provenance and never pretends
to be an AI model.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.diagnosis.evidence_scorer import EvidenceScorer
from src.diagnosis.schema import CandidateCause, DiagnosticReport, DiagnosticStatus, ProbabilityBand
from src.diagnosis.session import DiagnosisRequest
from src.retrieval.evidence import EvidencePackage, EvidenceSufficiencyLevel


class DeterministicFallbackEngine:
    """Synthesizes structured diagnostic reports directly from retrieved case evidence."""

    @classmethod
    def generate_report(
        cls,
        request: DiagnosisRequest,
        evidence: EvidencePackage,
        investigation_id: str,
        fallback_reason: Optional[str] = None,
    ) -> DiagnosticReport:
        """Constructs an evidence-grounded report from retrieved cases without LLM generation."""
        # 1. Determine status and handle zero/low evidence cases
        if not evidence.items or evidence.sufficiency.level == EvidenceSufficiencyLevel.INSUFFICIENT.value:
            return cls._build_insufficient_evidence_report(
                request=request,
                evidence=evidence,
                investigation_id=investigation_id,
                fallback_reason=fallback_reason,
            )

        # 2. Synthesize candidate causes directly from top evidence items
        candidate_causes: List[CandidateCause] = []
        for rank, item in enumerate(evidence.items[:3], start=1):
            band = (
                ProbabilityBand.LIKELY.value
                if item.composite_score >= 0.70
                else ProbabilityBand.POSSIBLE.value
            )

            explanation = (
                f"Historical case precedent [{item.case_id}] ('{item.source_title}') documents "
                f"a confirmed root cause of: '{item.confirmed_root_cause}'. "
                f"Observed symptoms ({', '.join(request.symptoms)}) and diagnostic fault code "
                f"('{request.fault_code or 'None'}') exhibit a similarity score of {item.similarity_score:.4f} "
                f"(composite ranking: {item.composite_score:.4f})."
            )

            checks: List[str] = [
                f"Verify physical assembly and terminal connections for subsystem '{item.subsystem}'.",
                "Measure DC/AC operating supply rails against OEM nominal tolerances.",
            ]
            if item.candidate_propagation:
                checks.append(
                    f"Coupled Subsystem Check ({item.candidate_propagation.source_subsystem} ➔ {item.candidate_propagation.target_subsystem}): "
                    f"{item.candidate_propagation.diagnostic_check}"
                )

            actions = [item.corrective_action]

            candidate_causes.append(
                CandidateCause(
                    rank=rank,
                    hypothesis_title=item.confirmed_root_cause,
                    subsystem=item.subsystem,
                    probability_band=band,
                    explanation=explanation,
                    supporting_case_ids=[item.case_id],
                    conflicting_evidence=[],
                    recommended_checks=checks,
                    documented_corrective_actions=actions,
                )
            )

        # 3. Formulate executive summary
        top_cause = candidate_causes[0]
        summary = (
            f"Deterministic Knowledge Match (Fallback Mode): Identified {len(candidate_causes)} candidate "
            f"root cause(s) from historical elevator records. Primary hypothesis is '{top_cause.hypothesis_title}' "
            f"supported by historical incident [{top_cause.supporting_case_ids[0]}]."
        )

        # 4. Formulate uncertainty items
        uncertainties: List[str] = [
            "Diagnostic reasoning generated via deterministic historical case mapping (offline fallback mode).",
        ]
        if not request.fault_code:
            uncertainties.append("No OEM controller diagnostic trouble code provided; relying purely on symptom similarity.")
        if not request.telemetry:
            uncertainties.append("Sensor telemetry readings not supplied; operating parameters could not be verified.")

        # 5. Safety advisories
        safety = [
            "Mandatory Lock-Out / Tag-Out (LOTO): Isolate and lock the mainline disconnect before touching drive or motor wiring.",
            "Verify car is stationary and counterweight buffer space is verified before top-of-car inspection.",
            "Check safety string continuity with calibrated multimeter; do NOT place jumper clips across safety contacts.",
        ]

        confidence, breakdown = EvidenceScorer.compute_confidence(
            evidence_items=evidence.items,
            request_symptoms=request.symptoms,
            request_fault_code=request.fault_code,
            request_subsystem=request.subsystem,
            request_telemetry=request.telemetry,
            verification_verdict=None,
            is_verified=False,
        )

        model_meta = {
            "mode": "deterministic_fallback",
            "reason": fallback_reason or "Offline demo mode or non-LLM execution requested",
            "retrieved_count": len(evidence.items),
            "sufficiency_level": evidence.sufficiency.level,
            "confidence_breakdown": breakdown.to_dict(),
        }

        return DiagnosticReport(
            investigation_id=investigation_id,
            elevator_id=request.elevator_id,
            subsystem=request.subsystem,
            fault_code=request.fault_code,
            status=DiagnosticStatus.FALLBACK_DETERMINISTIC.value,
            summary=summary,
            candidate_causes=candidate_causes,
            uncertainty_and_missing_info=uncertainties,
            safety_advisories=safety,
            retrieved_case_ids=evidence.case_ids,
            generation_mode="fallback_deterministic",
            model_metadata=model_meta,
            confidence_score=confidence,
        )

    @classmethod
    def _build_insufficient_evidence_report(
        cls,
        request: DiagnosisRequest,
        evidence: EvidencePackage,
        investigation_id: str,
        fallback_reason: Optional[str] = None,
    ) -> DiagnosticReport:
        """Constructs an explicit insufficient-evidence diagnostic report."""
        summary = (
            f"Insufficient Historical Evidence: No close historical matches found in the knowledge base "
            f"for subsystem '{request.subsystem}' with reported symptoms. Preliminary physical fault isolation "
            f"protocol is required."
        )

        cause = CandidateCause(
            rank=1,
            hypothesis_title=f"Unindexed or novel fault condition in '{request.subsystem}'",
            subsystem=request.subsystem,
            probability_band=ProbabilityBand.UNLIKELY.value,
            explanation=(
                "Query symptoms fall below the semantic similarity threshold. "
                "The failure mode may involve intermittent physical binding, contact corrosion, "
                "or component failure not previously documented in benchmark cases."
            ),
            supporting_case_ids=[],
            conflicting_evidence=[],
            recommended_checks=[
                "Perform physical visual inspection of subsystem mechanical linkages.",
                "Review controller event history buffer on the machine room diagnostic tool.",
                "Verify sensor supply voltage and ground continuity.",
            ],
            documented_corrective_actions=[
                "Clean and lubricate mechanical movement per manufacturer specifications.",
                "Inspect wire harnesses for pinch points, chafing, or ground faults.",
            ],
        )

        uncertainties = [
            "Low textual similarity to existing knowledge base cases.",
            "Potential novel or uncatalogued failure mechanism.",
        ]

        safety = [
            "Place elevator on INDEPENDENT SERVICE before entering hoistway or pit.",
            "Verify safety circuit integrity prior to manual movement.",
        ]

        confidence, breakdown = EvidenceScorer.compute_confidence(
            evidence_items=evidence.items,
            request_symptoms=request.symptoms,
            request_fault_code=request.fault_code,
            request_subsystem=request.subsystem,
            request_telemetry=request.telemetry,
            verification_verdict="insufficient",
            is_verified=False,
        )

        return DiagnosticReport(
            investigation_id=investigation_id,
            elevator_id=request.elevator_id,
            subsystem=request.subsystem,
            fault_code=request.fault_code,
            status=DiagnosticStatus.INSUFFICIENT_EVIDENCE.value,
            summary=summary,
            candidate_causes=[cause],
            uncertainty_and_missing_info=uncertainties,
            safety_advisories=safety,
            retrieved_case_ids=evidence.case_ids,
            generation_mode="fallback_deterministic",
            model_metadata={
                "mode": "deterministic_fallback",
                "reason": fallback_reason or "Insufficient evidence in knowledge base",
                "confidence_breakdown": breakdown.to_dict(),
            },
            confidence_score=confidence,
        )
