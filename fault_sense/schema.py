"""FaultSense Schema Definitions and Data Validation.

Defines the core schema for elevator fault cases, including allowed enums,
strict field validations, and provenance/synthetic case guarantees.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class SubsystemType(str, Enum):
    """Recognized elevator subsystems."""
    DOOR_SYSTEM = "door_system"
    TRACTION_DRIVE = "traction_drive"
    HYDRAULIC_SYSTEM = "hydraulic_system"
    BRAKING_SYSTEM = "braking_system"
    SAFETY_GEAR = "safety_gear"
    CONTROLLER_ELECTRONICS = "controller_electronics"
    HOISTWAY_SIGNALING = "hoistway_signaling"
    CAR_INTERIOR_FIXTURES = "car_interior_fixtures"
    OTHER = "other"

    @classmethod
    def from_str(cls, val: str) -> str:
        val_clean = val.strip().lower().replace(" ", "_").replace("-", "_")
        for member in cls:
            if member.value == val_clean or member.name.lower() == val_clean:
                return member.value
        return cls.OTHER.value


class SourceType(str, Enum):
    """Origin categories for fault cases."""
    SYNTHETIC_ILLUSTRATIVE = "synthetic_illustrative"
    FIELD_SERVICE_LOG = "field_service_log"
    INCIDENT_INVESTIGATION = "incident_investigation"
    MAINTENANCE_RECORD = "maintenance_record"
    OEM_TECHNICAL_BULLETIN = "oem_technical_bulletin"
    TELEMETRY_ALARM_LOG = "telemetry_alarm_log"
    OTHER = "other"

    @classmethod
    def from_str(cls, val: str) -> str:
        val_clean = val.strip().lower().replace(" ", "_").replace("-", "_")
        for member in cls:
            if member.value == val_clean or member.name.lower() == val_clean:
                return member.value
        return cls.OTHER.value


class VerificationStatus(str, Enum):
    """Verification state for fault record diagnostics."""
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    IN_REVIEW = "in_review"

    @classmethod
    def from_str(cls, val: str) -> str:
        val_clean = val.strip().lower().replace(" ", "_").replace("-", "_")
        for member in cls:
            if member.value == val_clean or member.name.lower() == val_clean:
                return member.value
        return cls.UNVERIFIED.value


class FaultCaseValidationError(ValueError):
    """Raised when fault case attributes fail validation."""

    def __init__(self, message: str, field_name: Optional[str] = None, invalid_value: Any = None):
        super().__init__(message)
        self.message = message
        self.field_name = field_name
        self.invalid_value = invalid_value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field_name,
            "message": self.message,
            "invalid_value": str(self.invalid_value) if self.invalid_value is not None else None,
        }


@dataclass
class FaultCase:
    """Represents a validated elevator fault case.

    Attributes:
        case_id: Unique record identifier (e.g. 'CASE-ELEV-001').
        source_title: Title or subject of the original documentation/ticket.
        source_reference: Source reference (ticket #, bulletin ID, URL, etc.).
        source_type: Origin type (e.g. 'synthetic_illustrative', 'field_service_log').
        verification_status: Verification state ('verified', 'unverified', 'in_review').
        subsystem: Elevator subsystem affected.
        fault_code: Standard or manufacturer fault code (e.g. 'E-201', 'DR-302').
        symptoms: List of observed operational or sensory symptoms.
        telemetry_summary: Dict of telemetry / sensor summary statistics.
        confirmed_root_cause: Confirmed mechanical, electrical, or software root cause.
        corrective_action: Work performed to resolve the fault.
        timestamp: Optional ISO 8601 timestamp string of incident or recording.
        metadata: Optional dictionary for custom tags, building info, model details.
        is_indexed: Flag indicating if the case has been indexed into vector storage.
        indexed_at: Timestamp when indexing occurred.
    """

    case_id: str
    source_title: str
    source_reference: str
    source_type: str
    verification_status: str
    subsystem: str
    fault_code: str
    symptoms: List[str]
    telemetry_summary: Dict[str, Any]
    confirmed_root_cause: str
    corrective_action: str
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_indexed: bool = False
    indexed_at: Optional[str] = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Performs rigorous schema and provenance validation."""
        # Validate case_id
        if not isinstance(self.case_id, str) or not self.case_id.strip():
            raise FaultCaseValidationError(
                "case_id must be a non-empty string.", field_name="case_id", invalid_value=self.case_id
            )
        self.case_id = self.case_id.strip()

        # Validate source_title
        if not isinstance(self.source_title, str) or not self.source_title.strip():
            raise FaultCaseValidationError(
                "source_title must be a non-empty string.", field_name="source_title", invalid_value=self.source_title
            )
        self.source_title = self.source_title.strip()

        # Validate source_reference
        if not isinstance(self.source_reference, str) or not self.source_reference.strip():
            raise FaultCaseValidationError(
                "source_reference must be a non-empty string.",
                field_name="source_reference",
                invalid_value=self.source_reference,
            )
        self.source_reference = self.source_reference.strip()

        # Normalize & validate source_type
        if not isinstance(self.source_type, str) or not self.source_type.strip():
            raise FaultCaseValidationError(
                "source_type must be a non-empty string.", field_name="source_type", invalid_value=self.source_type
            )
        self.source_type = SourceType.from_str(self.source_type)

        # Normalize & validate verification_status
        if not isinstance(self.verification_status, str) or not self.verification_status.strip():
            raise FaultCaseValidationError(
                "verification_status must be a non-empty string.",
                field_name="verification_status",
                invalid_value=self.verification_status,
            )
        self.verification_status = VerificationStatus.from_str(self.verification_status)

        # Normalize & validate subsystem
        if not isinstance(self.subsystem, str) or not self.subsystem.strip():
            raise FaultCaseValidationError(
                "subsystem must be a non-empty string.", field_name="subsystem", invalid_value=self.subsystem
            )
        self.subsystem = SubsystemType.from_str(self.subsystem)

        # Validate fault_code
        if not isinstance(self.fault_code, str) or not self.fault_code.strip():
            raise FaultCaseValidationError(
                "fault_code must be a non-empty string.", field_name="fault_code", invalid_value=self.fault_code
            )
        self.fault_code = self.fault_code.strip()

        # Validate symptoms
        if not isinstance(self.symptoms, list):
            raise FaultCaseValidationError(
                "symptoms must be a list of non-empty strings.", field_name="symptoms", invalid_value=self.symptoms
            )
        cleaned_symptoms: List[str] = []
        for s in self.symptoms:
            if isinstance(s, str) and s.strip():
                cleaned_symptoms.append(s.strip())
            elif isinstance(s, (int, float)):
                cleaned_symptoms.append(str(s).strip())
        if not cleaned_symptoms:
            raise FaultCaseValidationError(
                "symptoms list must contain at least one non-empty symptom description.",
                field_name="symptoms",
                invalid_value=self.symptoms,
            )
        self.symptoms = cleaned_symptoms

        # Validate telemetry_summary
        if not isinstance(self.telemetry_summary, dict):
            raise FaultCaseValidationError(
                "telemetry_summary must be a dictionary of sensor metrics.",
                field_name="telemetry_summary",
                invalid_value=self.telemetry_summary,
            )

        # Validate confirmed_root_cause
        if not isinstance(self.confirmed_root_cause, str) or not self.confirmed_root_cause.strip():
            raise FaultCaseValidationError(
                "confirmed_root_cause must be a non-empty string.",
                field_name="confirmed_root_cause",
                invalid_value=self.confirmed_root_cause,
            )
        self.confirmed_root_cause = self.confirmed_root_cause.strip()

        # Validate corrective_action
        if not isinstance(self.corrective_action, str) or not self.corrective_action.strip():
            raise FaultCaseValidationError(
                "corrective_action must be a non-empty string.",
                field_name="corrective_action",
                invalid_value=self.corrective_action,
            )
        self.corrective_action = self.corrective_action.strip()

        # Validate optional timestamp
        if self.timestamp is not None:
            if isinstance(self.timestamp, str) and self.timestamp.strip():
                self.timestamp = self._normalize_timestamp(self.timestamp.strip())
            else:
                self.timestamp = None

        # Validate metadata
        if self.metadata is None:
            self.metadata = {}
        elif not isinstance(self.metadata, dict):
            raise FaultCaseValidationError(
                "metadata must be a dictionary.", field_name="metadata", invalid_value=self.metadata
            )

        # Enforce Synthetic & Provenance Distinction:
        # If source_type is synthetic_illustrative or marked synthetic, ensure metadata indicates is_synthetic
        is_synthetic_type = self.source_type == SourceType.SYNTHETIC_ILLUSTRATIVE.value
        is_synthetic_meta = bool(self.metadata.get("is_synthetic", False))

        if is_synthetic_type or is_synthetic_meta:
            self.metadata["is_synthetic"] = True
            # Synthetic illustrative cases must never be falsely marked as verified historical incidents
            if self.verification_status == VerificationStatus.VERIFIED.value:
                # Disallow claiming synthetic examples are verified incidents
                raise FaultCaseValidationError(
                    "Illustrative synthetic cases cannot be marked as verified historical incidents. "
                    "Must be labeled 'unverified' or 'in_review'.",
                    field_name="verification_status",
                    invalid_value=self.verification_status,
                )
        else:
            self.metadata.setdefault("is_synthetic", False)

    @staticmethod
    def _normalize_timestamp(ts_str: str) -> str:
        """Normalizes various timestamp strings into ISO 8601 UTC format."""
        try:
            # Handle ISO string or common formats
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            return dt.isoformat()
        except Exception:
            # If standard parser fails, return trimmed original if valid non-empty
            return ts_str

    @property
    def is_synthetic(self) -> bool:
        """Convenience property for synthetic case check."""
        return bool(self.metadata.get("is_synthetic", False)) or (
            self.source_type == SourceType.SYNTHETIC_ILLUSTRATIVE.value
        )

    def to_dict(self) -> Dict[str, Any]:
        """Converts case to dictionary representation."""
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FaultCase:
        """Creates a FaultCase instance from a dictionary, with type coercions."""
        if not isinstance(data, dict):
            raise FaultCaseValidationError("Expected dictionary for FaultCase instantiation.", invalid_value=data)

        # Copy data so we do not mutate original
        raw = dict(data)

        # Coerce symptoms if passed as string / JSON string
        symptoms = raw.get("symptoms")
        if isinstance(symptoms, str):
            symptoms_str = symptoms.strip()
            if symptoms_str.startswith("[") and symptoms_str.endswith("]"):
                try:
                    symptoms = json.loads(symptoms_str)
                except Exception:
                    symptoms = [s.strip() for s in symptoms_str.split(";") if s.strip()]
            else:
                # Comma or semicolon separated
                sep = ";" if ";" in symptoms_str else ","
                symptoms = [s.strip() for s in symptoms_str.split(sep) if s.strip()]
            raw["symptoms"] = symptoms

        # Coerce telemetry_summary if passed as JSON string
        telemetry = raw.get("telemetry_summary")
        if isinstance(telemetry, str):
            telemetry_str = telemetry.strip()
            if telemetry_str.startswith("{") and telemetry_str.endswith("}"):
                try:
                    telemetry = json.loads(telemetry_str)
                except Exception:
                    telemetry = {}
            else:
                telemetry = {}
            raw["telemetry_summary"] = telemetry
        elif telemetry is None:
            raw["telemetry_summary"] = {}

        # Coerce metadata if passed as JSON string
        metadata = raw.get("metadata")
        if isinstance(metadata, str):
            meta_str = metadata.strip()
            if meta_str.startswith("{") and meta_str.endswith("}"):
                try:
                    metadata = json.loads(meta_str)
                except Exception:
                    metadata = {}
            else:
                metadata = {}
            raw["metadata"] = metadata
        elif metadata is None:
            raw["metadata"] = {}

        # Coerce is_indexed
        is_indexed_val = raw.get("is_indexed", False)
        if isinstance(is_indexed_val, (int, str)):
            raw["is_indexed"] = bool(is_indexed_val) and str(is_indexed_val).lower() not in ("0", "false")

        # Required fields mapping
        return cls(
            case_id=str(raw.get("case_id", "")),
            source_title=str(raw.get("source_title", "")),
            source_reference=str(raw.get("source_reference", "")),
            source_type=str(raw.get("source_type", "")),
            verification_status=str(raw.get("verification_status", "")),
            subsystem=str(raw.get("subsystem", "")),
            fault_code=str(raw.get("fault_code", "")),
            symptoms=raw.get("symptoms", []),
            telemetry_summary=raw.get("telemetry_summary", {}),
            confirmed_root_cause=str(raw.get("confirmed_root_cause", "")),
            corrective_action=str(raw.get("corrective_action", "")),
            timestamp=raw.get("timestamp"),
            metadata=raw.get("metadata", {}),
            is_indexed=raw.get("is_indexed", False),
            indexed_at=raw.get("indexed_at"),
        )

    def to_json(self, indent: Optional[int] = 2) -> str:
        """Serializes case to JSON formatted string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_json(cls, json_str: str) -> FaultCase:
        """Deserializes JSON string into a FaultCase."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise FaultCaseValidationError(f"Invalid JSON content: {exc}") from exc
        return cls.from_dict(data)

    def to_embedding_text(self, format_style: str = "rich") -> str:
        """Formats the case into an information-dense text representation for vector indexing."""
        symptoms_str = "; ".join(self.symptoms)
        telemetry_items = [f"{k}={v}" for k, v in sorted(self.telemetry_summary.items())]
        telemetry_str = ", ".join(telemetry_items) if telemetry_items else "None recorded"
        provenance = "SYNTHETIC ILLUSTRATIVE" if self.is_synthetic else "REAL OPERATIONAL RECORD"

        if format_style == "compact":
            return (
                f"Subsystem: {self.subsystem} | Code: {self.fault_code} | Symptoms: {symptoms_str} | "
                f"Root Cause: {self.confirmed_root_cause} | Action: {self.corrective_action} | "
                f"Status: {self.verification_status} ({provenance})"
            )

        # Rich multi-line format
        return (
            f"[ELEVATOR FAULT CASE: {self.case_id}]\n"
            f"Provenance: {provenance} (Type: {self.source_type}, Status: {self.verification_status})\n"
            f"Source Document: {self.source_title} (Ref: {self.source_reference})\n"
            f"Subsystem: {self.subsystem}\n"
            f"Fault Code: {self.fault_code}\n"
            f"Observed Symptoms: {symptoms_str}\n"
            f"Telemetry Summary: {telemetry_str}\n"
            f"Confirmed Root Cause: {self.confirmed_root_cause}\n"
            f"Corrective Action Taken: {self.corrective_action}\n"
            f"Timestamp: {self.timestamp or 'N/A'}"
        )
