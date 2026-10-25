"""Domain models for technician diagnosis and fault isolation sessions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class DiagnosisRequest:
    """Technician input specification for an investigation session."""
    elevator_id: str
    subsystem: str
    fault_code: Optional[str] = None
    symptoms: List[str] = field(default_factory=list)
    telemetry: Dict[str, Any] = field(default_factory=dict)
    building_id: Optional[str] = None
    technician_notes: Optional[str] = None
    manufacturer: Optional[str] = None
    equipment_model: Optional[str] = None
    problem_description: Optional[str] = None
    operating_conditions: Optional[str] = None
    severity: Optional[str] = None


@dataclass
class DiagnosisResult:
    """Structured diagnostic recommendations returned by the diagnosis engine."""
    investigation_id: str
    elevator_id: str
    subsystem: str
    root_cause_hypothesis: str
    confidence_score: float
    recommended_actions: List[str]
    matched_cases: List[Dict[str, Any]]
    is_ai_generated: bool
    mode_notice: str
    evidence_package: Optional[Dict[str, Any]] = None
    diagnostic_report: Optional[Dict[str, Any]] = None
    generation_mode: str = "fallback_deterministic"
    sufficiency_level: str = "moderate"
    warnings: List[str] = field(default_factory=list)
    verification_record: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    is_verified: bool = False
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
