"""Unit tests for FaultSense schema validation, serialization, and provenance rules."""

import json
import unittest

from fault_sense.schema import (
    FaultCase,
    FaultCaseValidationError,
    SourceType,
    SubsystemType,
    VerificationStatus,
)


class TestFaultCaseSchema(unittest.TestCase):
    """Tests schema validation, normalization, and provenance guarantees."""

    def setUp(self):
        self.valid_data = {
            "case_id": "CASE-TEST-001",
            "source_title": "Field Service Report #1024",
            "source_reference": "FSR-1024",
            "source_type": "field_service_log",
            "verification_status": "verified",
            "subsystem": "door_system",
            "fault_code": "E-DR-101",
            "symptoms": ["Door reopens repeatedly", "Obstruction warning on panel"],
            "telemetry_summary": {"door_cycles": 5000, "motor_temp_c": 45.2},
            "confirmed_root_cause": "Misaligned photo-eye bracket on door header",
            "corrective_action": "Realigned photo-eye sensor and tested 15 cycles",
            "timestamp": "2024-10-15T10:00:00Z",
            "metadata": {"elevator_id": "ELV-04", "building": "Tower A"},
        }

    def test_valid_case_creation(self):
        """A properly formatted record should instantiate and validate successfully."""
        fc = FaultCase.from_dict(self.valid_data)
        self.assertEqual(fc.case_id, "CASE-TEST-001")
        self.assertEqual(fc.subsystem, "door_system")
        self.assertEqual(fc.verification_status, "verified")
        self.assertEqual(len(fc.symptoms), 2)
        self.assertFalse(fc.is_synthetic)
        self.assertFalse(fc.is_indexed)

    def test_empty_case_id_rejected(self):
        """Missing or blank case_id should raise FaultCaseValidationError."""
        data = dict(self.valid_data)
        data["case_id"] = "   "
        with self.assertRaises(FaultCaseValidationError) as ctx:
            FaultCase.from_dict(data)
        self.assertEqual(ctx.exception.field_name, "case_id")

    def test_empty_subsystem_rejected(self):
        """Empty subsystem should raise FaultCaseValidationError."""
        data = dict(self.valid_data)
        data["subsystem"] = ""
        with self.assertRaises(FaultCaseValidationError) as ctx:
            FaultCase.from_dict(data)
        self.assertEqual(ctx.exception.field_name, "subsystem")

    def test_subsystem_normalization(self):
        """Subsystem should normalize hyphenated or case variants."""
        data = dict(self.valid_data)
        data["subsystem"] = "DOOR-SYSTEM"
        fc = FaultCase.from_dict(data)
        self.assertEqual(fc.subsystem, SubsystemType.DOOR_SYSTEM.value)

    def test_empty_symptoms_rejected(self):
        """Symptoms list cannot be empty."""
        data = dict(self.valid_data)
        data["symptoms"] = []
        with self.assertRaises(FaultCaseValidationError) as ctx:
            FaultCase.from_dict(data)
        self.assertEqual(ctx.exception.field_name, "symptoms")

    def test_symptoms_coercion_from_string(self):
        """Symptoms passed as semicolon-separated string should parse into a list."""
        data = dict(self.valid_data)
        data["symptoms"] = "Door buzzer sounding; Optical curtain flicker"
        fc = FaultCase.from_dict(data)
        self.assertEqual(len(fc.symptoms), 2)
        self.assertEqual(fc.symptoms[0], "Door buzzer sounding")

    def test_symptoms_coercion_from_json_string(self):
        """Symptoms passed as JSON array string should parse into a list."""
        data = dict(self.valid_data)
        data["symptoms"] = '["Symptom A", "Symptom B"]'
        fc = FaultCase.from_dict(data)
        self.assertEqual(fc.symptoms, ["Symptom A", "Symptom B"])

    def test_telemetry_coercion_from_json_string(self):
        """Telemetry summary passed as JSON string should parse into a dictionary."""
        data = dict(self.valid_data)
        data["telemetry_summary"] = '{"voltage_v": 24.5, "alarm_active": true}'
        fc = FaultCase.from_dict(data)
        self.assertIsInstance(fc.telemetry_summary, dict)
        self.assertEqual(fc.telemetry_summary["voltage_v"], 24.5)

    def test_synthetic_provenance_enforcement(self):
        """Synthetic illustrative cases must be labeled synthetic and CANNOT claim verified incident status."""
        data = dict(self.valid_data)
        data["source_type"] = "synthetic_illustrative"
        data["verification_status"] = "verified"

        with self.assertRaises(FaultCaseValidationError) as ctx:
            FaultCase.from_dict(data)
        self.assertIn("Illustrative synthetic cases cannot be marked as verified", ctx.exception.message)

    def test_synthetic_auto_flag_in_metadata(self):
        """Synthetic source_type should automatically set metadata['is_synthetic'] = True."""
        data = dict(self.valid_data)
        data["source_type"] = "synthetic_illustrative"
        data["verification_status"] = "unverified"
        fc = FaultCase.from_dict(data)
        self.assertTrue(fc.is_synthetic)
        self.assertTrue(fc.metadata.get("is_synthetic"))

    def test_serialization_roundtrip(self):
        """FaultCase should serialize to and deserialize from JSON without data loss."""
        fc = FaultCase.from_dict(self.valid_data)
        json_str = fc.to_json()
        restored = FaultCase.from_json(json_str)
        self.assertEqual(fc.case_id, restored.case_id)
        self.assertEqual(fc.symptoms, restored.symptoms)
        self.assertEqual(fc.telemetry_summary, restored.telemetry_summary)
        self.assertEqual(fc.metadata, restored.metadata)

    def test_to_embedding_text_formats(self):
        """to_embedding_text should produce both rich and compact representations."""
        fc = FaultCase.from_dict(self.valid_data)
        rich_text = fc.to_embedding_text(format_style="rich")
        self.assertIn("[ELEVATOR FAULT CASE: CASE-TEST-001]", rich_text)
        self.assertIn("Confirmed Root Cause:", rich_text)

        compact_text = fc.to_embedding_text(format_style="compact")
        self.assertTrue(compact_text.startswith("Subsystem: door_system"))


if __name__ == "__main__":
    unittest.main()
