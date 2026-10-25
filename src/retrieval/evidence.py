"""Structured evidence package models and sufficiency evaluation for FaultSense.

Encapsulates retrieved case evidence, provenance, similarity metrics, multi-attribute
ranking rationales, candidate fault propagation hypotheses, and evidence sufficiency assessments.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from src.retrieval.topology import CandidatePropagation


class EvidenceSufficiencyLevel(str, Enum):
    """Categorical evaluation of retrieved evidence sufficiency for decision support."""
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    INSUFFICIENT = "insufficient"


@dataclass
class EvidenceQuery:
    """Technician query parameters submitted for historical evidence retrieval."""
    symptoms: List[str]
    fault_code: Optional[str] = None
    subsystem: Optional[str] = None
    telemetry: Dict[str, Any] = field(default_factory=dict)
    formulated_text: str = ""
    top_k: int = 5
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MatchRationale:
    """Detailed breakdown of individual signal contributions to the composite ranking score."""
    semantic_similarity: float
    exact_fault_code_match: bool
    exact_subsystem_match: bool
    telemetry_feature_overlap: float
    composite_score: float
    weights_applied: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceItem:
    """A single retrieved historical fault case with traceable provenance and evidence rationale."""
    case_id: str
    rank: int
    similarity_score: float  # Raw cosine similarity [-1.0, 1.0]
    composite_score: float   # Ranked score [0.0, 1.0]
    subsystem: str
    fault_code: str
    symptoms: List[str]
    telemetry_summary: Dict[str, Any]
    confirmed_root_cause: str
    corrective_action: str
    source_title: str
    source_reference: str
    source_type: str
    verification_status: str
    is_synthetic: bool
    match_rationale: MatchRationale
    candidate_propagation: Optional[CandidatePropagation] = None
    document_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.candidate_propagation:
            d["candidate_propagation"] = self.candidate_propagation.to_dict()
        d["match_rationale"] = self.match_rationale.to_dict()
        return d


@dataclass
class EvidenceSufficiency:
    """Evaluation of whether retrieved evidence provides reliable basis for diagnosis."""
    level: str  # High, Moderate, Low, Insufficient
    is_sufficient: bool
    top_similarity: float
    corroborating_case_count: int
    reasons: List[str] = field(default_factory=list)
    disclaimer: str = (
        "Notice: Similarity scores measure textual vector closeness in the embedding space. "
        "They do NOT represent a statistical probability of diagnostic correctness. "
        "All recommendations require on-site electrical, mechanical, and safety verification."
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvidencePackage:
    """Complete structured evidence payload delivered to the diagnostic engine or technician."""
    query: EvidenceQuery
    items: List[EvidenceItem]
    total_candidates_searched: int
    returned_count: int
    sufficiency: EvidenceSufficiency
    filter_explanation: str
    ranking_strategy: str
    warnings: List[str] = field(default_factory=list)

    @property
    def case_ids(self) -> List[str]:
        return [item.case_id for item in self.items]

    @property
    def has_high_evidence(self) -> bool:
        return self.sufficiency.level in (EvidenceSufficiencyLevel.HIGH.value, EvidenceSufficiencyLevel.MODERATE.value)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query.to_dict(),
            "items": [it.to_dict() for it in self.items],
            "total_candidates_searched": self.total_candidates_searched,
            "returned_count": self.returned_count,
            "sufficiency": self.sufficiency.to_dict(),
            "filter_explanation": self.filter_explanation,
            "ranking_strategy": self.ranking_strategy,
            "warnings": self.warnings,
            "retrieved_case_ids": self.case_ids,
        }

    def summary_markdown(self) -> str:
        """Renders a formatted Markdown summary suitable for terminal or Streamlit display."""
        lines = [
            f"### FaultSense Evidence Package",
            f"**Query**: Subsystem: `{self.query.subsystem or 'Any'}` | Fault Code: `{self.query.fault_code or 'None'}`",
            f"**Symptoms**: {', '.join(self.query.symptoms) if self.query.symptoms else 'None'}",
            f"**Evidence Sufficiency**: **{self.sufficiency.level.upper()}** (Sufficient: `{self.sufficiency.is_sufficient}`)",
            f"**Candidates Evaluated**: {self.total_candidates_searched} | **Returned**: {self.returned_count}",
        ]

        if self.warnings:
            lines.append(f"\n> **Warnings**:")
            for w in self.warnings:
                lines.append(f"> - {w}")

        lines.append(f"\n#### Retrieved Cases:")
        if not self.items:
            lines.append("_No matching historical cases found._")
        else:
            for it in self.items:
                prov = "Synthetic" if it.is_synthetic else "Verified"
                lines.append(
                    f"- **#{it.rank} [{it.case_id}]** (`{it.subsystem}` / `{it.fault_code}`) — "
                    f"**Cosine Sim**: `{it.similarity_score:.4f}` | **Composite**: `{it.composite_score:.4f}` | "
                    f"_{it.source_title}_ ({prov})"
                )
                lines.append(f"  - **Root Cause**: {it.confirmed_root_cause}")
                lines.append(f"  - **Action**: {it.corrective_action}")
                if it.candidate_propagation:
                    lines.append(
                        f"  - **Candidate Propagation** (`{it.candidate_propagation.source_subsystem}` -> `{it.candidate_propagation.target_subsystem}`): "
                        f"{it.candidate_propagation.propagation_mechanism}"
                    )

        return "\n".join(lines)
