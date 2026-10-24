"""Validator and citation verification guardrails for LLM diagnostic output.

Performs robust JSON extraction, schema validation, and strict citation verification
to ensure that every cited case exists in the retrieved evidence package.
Sanitizes hallucinated case IDs and formats output into validated DiagnosticReport objects.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Set

from src.diagnosis.llm.base import LLMResponse, LLMResponseFormatError
from src.diagnosis.schema import CandidateCause, DiagnosticReport, DiagnosticStatus, ProbabilityBand
from src.diagnosis.session import DiagnosisRequest
from src.retrieval.evidence import EvidencePackage
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DiagnosticValidator:
    """Validates raw LLM outputs, enforces citation integrity, and builds DiagnosticReport."""

    @classmethod
    def parse_and_validate(
        cls,
        llm_response: LLMResponse,
        request: DiagnosisRequest,
        evidence: EvidencePackage,
        investigation_id: str,
    ) -> DiagnosticReport:
        """Parses LLM response, validates citations, and constructs verified DiagnosticReport.

        Args:
            llm_response: Standardized response payload from LLM provider.
            request: Original technician diagnosis request.
            evidence: Evidence package containing retrieved cases and allowed citation IDs.
            investigation_id: Unique investigation tracking ID.

        Returns:
            Validated DiagnosticReport instance.

        Raises:
            LLMResponseFormatError: If response text cannot be parsed as JSON or lacks required fields.
        """
        raw_text = llm_response.content.strip()
        parsed_json = cls._extract_json(raw_text)

        allowed_ids: Set[str] = set(evidence.case_ids)

        # 1. Parse summary
        summary = str(parsed_json.get("summary") or "Diagnostic synthesis generated based on elevator telemetry.")

        # 2. Parse and validate candidate causes
        raw_candidates = parsed_json.get("candidate_causes", [])
        if not isinstance(raw_candidates, list) or len(raw_candidates) == 0:
            raise LLMResponseFormatError("LLM response lacks required 'candidate_causes' list.")

        validated_causes: List[CandidateCause] = []
        for rank, c_dict in enumerate(raw_candidates, start=1):
            if not isinstance(c_dict, dict):
                continue

            title = str(c_dict.get("hypothesis_title") or f"Candidate Hypothesis #{rank}")
            sub = str(c_dict.get("subsystem") or request.subsystem).lower().strip()

            raw_band = str(c_dict.get("probability_band") or "possible").lower().strip()
            if raw_band not in ("likely", "possible", "unlikely"):
                raw_band = "possible"

            explanation = str(c_dict.get("explanation") or "No detailed explanation provided.")

            # Validate citations against evidence package
            raw_cites = c_dict.get("supporting_case_ids", [])
            valid_cites: List[str] = []
            citation_warnings: List[str] = []

            if isinstance(raw_cites, list):
                for cid in raw_cites:
                    cid_str = str(cid).strip()
                    if cid_str in allowed_ids:
                        valid_cites.append(cid_str)
                    else:
                        warning = (
                            f"Hallucination Guard: Model cited unverified case_id '{cid_str}' "
                            f"which was not present in retrieved evidence. Citation suppressed."
                        )
                        citation_warnings.append(warning)
                        logger.warning(warning)

            conflicts = [str(x) for x in c_dict.get("conflicting_evidence", []) if str(x).strip()]
            checks = [str(x) for x in c_dict.get("recommended_checks", []) if str(x).strip()]
            actions = [str(x) for x in c_dict.get("documented_corrective_actions", []) if str(x).strip()]

            validated_causes.append(
                CandidateCause(
                    rank=rank,
                    hypothesis_title=title,
                    subsystem=sub,
                    probability_band=raw_band,
                    explanation=explanation,
                    supporting_case_ids=valid_cites,
                    conflicting_evidence=conflicts,
                    recommended_checks=checks,
                    documented_corrective_actions=actions,
                    citation_warnings=citation_warnings,
                )
            )

        # 3. Parse uncertainty and safety advisories
        uncertainties = [
            str(x) for x in parsed_json.get("uncertainty_and_missing_info", []) if str(x).strip()
        ]
        safety = [str(x) for x in parsed_json.get("safety_advisories", []) if str(x).strip()]
        if not safety:
            safety = [
                "Verify elevator is switched to INDEPENDENT / INSPECTION service before entering hoistway.",
                "Measure zero voltage across main disconnect switch before inspecting electrical components.",
            ]

        # 4. Parse confidence score (advisory only)
        raw_conf = parsed_json.get("confidence_score", 0.70)
        try:
            confidence = max(0.10, min(0.95, float(raw_conf)))
        except (ValueError, TypeError):
            confidence = 0.70

        model_meta = {
            "provider": llm_response.provider,
            "model": llm_response.model,
            "execution_time_s": llm_response.execution_time_s,
            "prompt_tokens": llm_response.prompt_tokens,
            "completion_tokens": llm_response.completion_tokens,
            "total_tokens": llm_response.total_tokens,
        }

        return DiagnosticReport(
            investigation_id=investigation_id,
            elevator_id=request.elevator_id,
            subsystem=request.subsystem,
            fault_code=request.fault_code,
            status=DiagnosticStatus.COMPLETED.value,
            summary=summary,
            candidate_causes=validated_causes,
            uncertainty_and_missing_info=uncertainties,
            safety_advisories=safety,
            retrieved_case_ids=evidence.case_ids,
            generation_mode="llm_reasoning",
            model_metadata=model_meta,
            confidence_score=round(confidence, 2),
        )

    @classmethod
    def _extract_json(cls, raw_text: str) -> Dict[str, Any]:
        """Extracts and parses JSON object from raw response string, handling markdown wrappers."""
        text = raw_text.strip()

        # Check for ```json ... ``` markdown block
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            text = match.group(1).strip()

        # Find outer braces if leading/trailing prose is present
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            text = text[start_idx : end_idx + 1]

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            # Attempt basic repair: remove trailing commas before closing braces
            cleaned = re.sub(r",\s*([\]}])", r"\1", text)
            try:
                return json.loads(cleaned)
            except Exception:
                raise LLMResponseFormatError(
                    f"Failed to parse LLM response as JSON: {exc}. Raw content preview: {raw_text[:200]}"
                ) from exc
