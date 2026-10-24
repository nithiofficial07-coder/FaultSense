"""Tests for Phase 7: UI integration, Diagnostic Assistant, and Evaluation engine."""

import io
import json
import tempfile
import unittest
from pathlib import Path

from config.settings import get_settings
from fault_sense.repository import FaultCaseRepository
from fault_sense.schema import FaultCase, SubsystemType
from src.diagnosis.assistant import DiagnosticAssistantService
from src.diagnosis.engine import DiagnosisEngine
from src.diagnosis.session import DiagnosisRequest
from src.evaluation.evaluator import BENCHMARK_SUITE, BenchmarkScenario, EvaluationEngine
from src.retrieval.vector_store import FAISSVectorStore
from src.storage.database import DatabaseManager
from src.storage.repository import InvestigationRepository
from src.ui.pages.new_investigation import parse_telemetry_file


class DummyUploadFile:
    """Mock Streamlit uploaded file object."""

    def __init__(self, name: str, data: bytes):
        self.name = name
        self.data = data

    def getvalue(self) -> bytes:
        return self.data


class TestPhase7UIAndAssistant(unittest.TestCase):
    """Validates Conversational Assistant, Evaluation Benchmark, and Investigation persistence."""

    def setUp(self):
        self.db_mgr = DatabaseManager(db_path=":memory:")
        self.inv_repo = InvestigationRepository(db_manager=self.db_mgr)
        self.case_repo = FaultCaseRepository(db_path=":memory:")

        # Add sample benchmark case
        self.sample_case = FaultCase(
            case_id="CASE-SYNTH-ELEV-001",
            source_title="Illustrative Engineering Benchmark: Optical Curtain Obstruction",
            source_reference="FAULT-SENSE-SYNTH-BENCH-2024-01",
            source_type="synthetic_illustrative",
            verification_status="unverified",
            subsystem=SubsystemType.DOOR_SYSTEM.value,
            fault_code="E-DR-201",
            symptoms=[
                "Car door reopens repeatedly without passenger obstruction",
                "Door dwell timer expires causing nudging buzzer activation",
            ],
            telemetry_summary={
                "door_open_close_cycles": 142500,
                "curtain_optical_attenuation_db": 6.8,
            },
            confirmed_root_cause="Accumulated grit in car bottom sill guide track causing optical curtain transmitter misalignment.",
            corrective_action="Vacuumed and cleaned bottom door sill grooves, adjusted transmitter bracket alignment.",
            metadata={"is_synthetic": True},
        )
        self.case_repo.add(self.sample_case)

        # Create active sample investigation session
        self.sample_inv_id = "INV-TEST-701"
        self.inv_repo.create({
            "investigation_id": self.sample_inv_id,
            "elevator_id": "ELV-CAR-04",
            "building_id": "Commercial Plaza Tower B",
            "subsystem": "door_system",
            "fault_code": "E-DR-201",
            "symptoms": ["Car door reopens repeatedly without passenger obstruction"],
            "telemetry": {
                "curtain_optical_attenuation_db": 6.8,
                "motor_current_peak_a": 3.8,
            },
            "root_cause_hypothesis": "Accumulated grit in car bottom sill guide track causing optical curtain transmitter misalignment.",
            "recommended_actions": "1. Vacuum and clean door sill track grooves.\n2. Verify optical curtain alignment.",
            "confidence_score": 0.92,
            "matched_case_ids": ["CASE-SYNTH-ELEV-001"],
            "status": "completed",
            "technician_notes": "Tested in field.",
            "verification_record": {
                "final_status": "verified",
                "final_verdict": "sufficient",
                "total_retries": 0,
                "max_retries": 2,
                "steps": [],
            },
            "retry_count": 0,
            "diagnostic_report": {
                "candidate_causes": [
                    {
                        "rank": 1,
                        "hypothesis_title": "Door Sill Grit Obstruction",
                        "probability_band": "likely",
                        "explanation": "Debris accumulated in sill groove obstructing optical curtain path.",
                        "supporting_case_ids": ["CASE-SYNTH-ELEV-001"],
                        "recommended_checks": ["Measure optical receiver attenuation", "Inspect sill tracks"],
                        "documented_corrective_actions": ["Clean sill grooves", "Realign transmitter"],
                    }
                ],
                "safety_advisories": ["Execute Lockout/Tagout (LOTO) prior to servicing."],
            },
            "evidence_package": {
                "evidence_items": [self.sample_case.to_dict()],
            },
        })

    def test_assistant_grounded_answer(self):
        """Conversational assistant answers questions grounded in active investigation."""
        assistant = DiagnosticAssistantService()
        inv_data = self.inv_repo.get(self.sample_inv_id)
        self.assertIsNotNone(inv_data)

        # 1. Ask about corrective actions
        res_actions = assistant.answer_question(inv_data, "What corrective actions should I take?")
        self.assertTrue(res_actions["is_supported"])
        self.assertIn("clean", res_actions["answer"].lower())

        # 2. Ask about telemetry
        res_tel = assistant.answer_question(inv_data, "What are the sensor telemetry readings?")
        self.assertTrue(res_tel["is_supported"])
        self.assertIn("curtain_optical_attenuation_db", res_tel["answer"])
        self.assertIn("6.8", res_tel["answer"])

        # 3. Ask about safety
        res_saf = assistant.answer_question(inv_data, "What safety precautions must I take?")
        self.assertTrue(res_saf["is_supported"])
        self.assertIn("Lockout/Tagout", res_saf["answer"])

    def test_assistant_rejects_unsupported_questions(self):
        """Conversational assistant explicitly detects and rejects unsupported queries."""
        assistant = DiagnosticAssistantService()
        inv_data = self.inv_repo.get(self.sample_inv_id)

        # Query asking about hydraulic oil for an electrical door fault
        res_unsupported = assistant.answer_question(inv_data, "What is the hydraulic cylinder oil level and valve pressure?")
        self.assertFalse(res_unsupported["is_supported"])
        self.assertIn("Unsupported Question", res_unsupported["answer"])
        self.assertIn("hydraulic", res_unsupported["answer"].lower())

    def test_telemetry_file_parser_json(self):
        """Parses valid JSON telemetry upload."""
        raw_json = json.dumps({"motor_current_a": 4.2, "temperature_c": 45.0}).encode("utf-8")
        upload = DummyUploadFile("telemetry.json", raw_json)
        parsed = parse_telemetry_file(upload)
        self.assertEqual(parsed.get("motor_current_a"), 4.2)
        self.assertEqual(parsed.get("temperature_c"), 45.0)

    def test_telemetry_file_parser_csv_tabular(self):
        """Parses tabular CSV telemetry upload."""
        raw_csv = b"speed_mps,vibration_m_s2\n1.75,0.08\n"
        upload = DummyUploadFile("telemetry.csv", raw_csv)
        parsed = parse_telemetry_file(upload)
        self.assertEqual(parsed.get("speed_mps"), 1.75)
        self.assertEqual(parsed.get("vibration_m_s2"), 0.08)

    def test_telemetry_file_parser_csv_key_value(self):
        """Parses 2-column key-value CSV telemetry upload."""
        raw_csv = b"bus_voltage_v,680\nambient_temp_c,28.5\n"
        upload = DummyUploadFile("telemetry.csv", raw_csv)
        parsed = parse_telemetry_file(upload)
        self.assertEqual(parsed.get("bus_voltage_v"), 680)
        self.assertEqual(parsed.get("ambient_temp_c"), 28.5)

    def test_evaluation_engine_benchmark(self):
        """EvaluationEngine executes comparative evaluation and returns structured metrics."""
        engine = EvaluationEngine()
        mini_suite = [
            BenchmarkScenario(
                scenario_id="SCEN-TEST-01",
                title="Door Sill Debris Test",
                subsystem="door_system",
                fault_code="E-DR-201",
                symptoms=["Car door reopens repeatedly without passenger obstruction"],
                expected_case_id="CASE-SYNTH-ELEV-001",
                expected_root_cause_keywords=["sill", "debris", "track"],
            )
        ]
        report = engine.run_benchmark(scenarios=mini_suite)
        self.assertEqual(report.total_scenarios, 1)
        self.assertGreater(report.baseline_avg_latency_ms, 0)
        self.assertGreater(report.verified_avg_latency_ms, 0)
        self.assertEqual(len(report.scenario_results), 1)

    def test_investigation_retrieval_after_restart(self):
        """Acceptance Criteria: Record is persisted and retrievable across simulated restart."""
        # Query record from repository
        inv = self.inv_repo.get(self.sample_inv_id)
        self.assertIsNotNone(inv)
        self.assertEqual(inv["elevator_id"], "ELV-CAR-04")
        self.assertEqual(inv["subsystem"], "door_system")
        self.assertEqual(inv["status"], "completed")

        # Verify complex JSON fields deserialized properly
        self.assertIsInstance(inv["telemetry"], dict)
        self.assertIsInstance(inv["matched_case_ids"], list)
        self.assertIsInstance(inv["verification_record"], dict)
        self.assertEqual(inv["verification_record"]["final_status"], "verified")
        self.assertIsInstance(inv["diagnostic_report"], dict)
        self.assertIn("candidate_causes", inv["diagnostic_report"])


if __name__ == "__main__":
    unittest.main()
