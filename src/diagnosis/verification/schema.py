"""Domain models and schemas for Phase 6 Agentic Self-Verification.

Defines fine-grained claim classification (supported, partially supported,
contradicted, unsupported), verification verdicts, and step-by-step audit history.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ClaimStatus(str, Enum):
    """Factual grounding classification for an individual diagnostic claim."""
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONTRADICTED = "contradicted"
    UNSUPPORTED = "unsupported"


class VerificationVerdict(str, Enum):
    """Aggregate verdict of the self-verification inspection."""
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    CONTRADICTED = "contradicted"
    INCONCLUSIVE = "inconclusive"


@dataclass
class ClaimVerification:
    """Detailed verification record for a specific diagnostic hypothesis or observation."""
    claim_text: str
    status: str  # ClaimStatus
    cited_case_ids: List[str] = field(default_factory=list)
    grounding_evidence: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    missing_evidence_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationResult:
    """Result of an evidence verification pass against a diagnostic draft."""
    verdict: str  # VerificationVerdict
    is_verified: bool
    verified_by: str  # "llm_verifier", "deterministic_verifier", etc.
    claims: List[ClaimVerification] = field(default_factory=list)
    supported_count: int = 0
    partially_supported_count: int = 0
    unsupported_count: int = 0
    contradicted_count: int = 0
    missing_evidence_reasons: List[str] = field(default_factory=list)
    suggested_query_refinements: List[str] = field(default_factory=list)
    is_fallback: bool = False
    limitations_notice: str = ""
    notes: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["claims"] = [c.to_dict() for c in self.claims]
        return d


@dataclass
class VerificationHistoryStep:
    """Auditable log entry for each iteration of the agentic verification loop."""
    step_number: int
    retrieval_query: str
    retrieved_case_ids: List[str]
    draft_summary: str
    draft_top_cause: Optional[str]
    verdict: str
    supported_claims: int
    unsupported_claims: int
    contradicted_claims: int
    reasons: List[str]
    action_taken: str  # "finalized", "re_retrieval_initiated", "max_retries_reached", "aborted_stale"
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationRecord:
    """Full audit trail of the self-verification lifecycle for an investigation."""
    investigation_id: str
    total_retries: int
    max_retries: int
    final_verdict: str
    final_status: str  # "verified_and_finalized", "inconclusive_max_retries", "inconclusive_insufficient_evidence", "rejected_contradicted"
    steps: List[VerificationHistoryStep] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["steps"] = [s.to_dict() for s in self.steps]
        return d
