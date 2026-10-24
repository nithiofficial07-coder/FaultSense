"""Document builder for converting elevator fault cases into searchable semantic text representations.

Formats structured attributes into reproducible, information-dense text documents
optimized for dense vector embedding models (e.g. all-MiniLM-L6-v2).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from fault_sense.schema import FaultCase


class DocumentBuilder:
    """Constructs structured, standardized semantic text documents from fault cases."""

    @staticmethod
    def build_document(case: FaultCase) -> str:
        """Transforms a single FaultCase into a canonical embedding text representation."""
        symptoms_str = "; ".join(case.symptoms) if case.symptoms else "None reported"

        # Telemetry summary formatting (key=value sorted for consistency)
        if case.telemetry_summary:
            telemetry_items = [f"{k}={v}" for k, v in sorted(case.telemetry_summary.items())]
            telemetry_str = ", ".join(telemetry_items)
        else:
            telemetry_str = "No sensor telemetry recorded"

        provenance = "Synthetic Benchmark" if case.is_synthetic else "Verified Incident"

        lines = [
            f"[ELEVATOR FAULT CASE: {case.case_id}]",
            f"Subsystem: {case.subsystem}",
            f"Fault Code: {case.fault_code}",
            f"Verification: {case.verification_status} ({provenance} | Origin: {case.source_type})",
            f"Source Document: {case.source_title} (Ref: {case.source_reference})",
            f"Observed Symptoms: {symptoms_str}",
            f"Telemetry Summary: {telemetry_str}",
            f"Confirmed Root Cause: {case.confirmed_root_cause}",
            f"Corrective Action Taken: {case.corrective_action}",
        ]

        if case.timestamp:
            lines.append(f"Recorded Timestamp: {case.timestamp}")

        return "\n".join(lines)

    @classmethod
    def build_documents_batch(cls, cases: Sequence[FaultCase]) -> List[str]:
        """Converts an iterable of FaultCases into canonical embedding documents."""
        return [cls.build_document(c) for c in cases]

    @staticmethod
    def build_query_document(
        query: str,
        subsystem: Optional[str] = None,
        fault_code: Optional[str] = None,
    ) -> str:
        """Constructs an asymmetric retrieval query document matching the indexing format."""
        parts = []
        if subsystem and subsystem.lower() not in ("all", "other", ""):
            parts.append(f"Subsystem: {subsystem.lower().strip()}")
        if fault_code and fault_code.strip():
            parts.append(f"Fault Code: {fault_code.strip()}")
        if query and query.strip():
            parts.append(f"Symptoms and Diagnostics: {query.strip()}")

        if not parts:
            return query.strip()

        return " | ".join(parts)
