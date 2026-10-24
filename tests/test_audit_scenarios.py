"""Automated Technical Audit Scenarios Suite (Scenarios A through K).

Tests all 11 required Master Audit End-to-End Scenarios:
- Scenario A: Standard diagnosis
- Scenario B: CSV telemetry ingestion and integration
- Scenario C: JSON fault data import and retrieval
- Scenario D: Insufficient evidence handling and uncertainty communication
- Scenario E: Unsupported diagnosis rejection by self-verification
- Scenario F: Verification retry limit bounding and inconclusive exit
- Scenario G: Provider timeout / failure and deterministic fallback
- Scenario H: SQLite persistence across application restarts
- Scenario I: Knowledge-base update and atomic index rebuild
- Scenario J: Evaluation pipeline execution and metric recording
- Scenario K: UI workflow simulation (session state, page routing, assistant scoping)
"""

import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fault_sense.ingestion import FaultCaseIngestionPipeline
from fault_sense.schema import FaultCase, SubsystemType
from src.diagnosis.assistant import DiagnosticAssistantService
from src.diagnosis.engine import DiagnosisEngine
from src.diagnosis.llm.providers import MockLLMProvider
from src.diagnosis.session import DiagnosisRequest
from src.evaluation.evaluator import EvaluationEngine
from src.retrieval.embeddings import DeterministicEmbeddingGenerator
from src.retrieval.index_manager import IndexManager
from src.retrieval.retrieval_service import FaultRetrievalService
from src.storage.database import DatabaseManager
from src.storage.repository import CaseRepository, InvestigationRepository


class TestAuditScenarios(unittest.TestCase):
    """Executes Master Audit Scenarios A through K."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.db_path = self.temp_path / "test_audit.db"
        self.index_dir = self.temp_path / "vector_store"
        self.index_dir.mkdir(parents=True, exist_ok=True)

        self.db_manager = DatabaseManager(self.db_path)
        self.db_manager.initialize_schema()
        self.case_repo = CaseRepository(self.db_path)
        self.inv_repo = InvestigationRepository(self.db_manager)

        self.embedder = DeterministicEmbeddingGenerator(dimension=384)

        # Populate initial test knowledge base case
        self.case_1 = FaultCase(
            case_id="AUDIT-CASE-001",
            source_title="OEM Bulletin: Door Sill Track Cleaning",
            source_reference="OEM-DR-2024-01",
            source_type="oem_advisory",
            verification_status="verified",
            subsystem="door_system",
            fault_code="E-DR-201",
            symptoms=[
                "Car door reopens repeatedly without passenger obstruction",
                "Door dwell timer buzzer sounding",
            ],
            telemetry_summary={"curtain_optical_attenuation_db": 6.8},
            confirmed_root_cause="Grit and debris accumulating in door sill guide grooves.",
            corrective_action="Vacuum bottom sill grooves and re-align optical transmitter.",
            metadata={"is_synthetic": False},
        )
        self.case_repo.create(self.case_1)

        self.idx_mgr = IndexManager(index_dir=self.index_dir, embedding_generator=self.embedder)
        self.idx_mgr.initialize(repo=self.case_repo, force_rebuild=True)
        self.retrieval_service = FaultRetrievalService(
            index_manager=self.idx_mgr,
            repository=self.case_repo,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_scenario_a_standard_diagnosis(self):
        """SCENARIO A: Standard Diagnosis end-to-end with evidence retrieval and verification."""
        engine = DiagnosisEngine(
            retrieval_service=self.retrieval_service,
            investigation_repo=self.inv_repo,
            enable_verification=True,
        )
        req = DiagnosisRequest(
            elevator_id="ELV-AUDIT-01",
            building_id="Audit Tower 1",
            subsystem="door_system",
            fault_code="E-DR-201",
            symptoms=["Car door reopens repeatedly without passenger obstruction"],
            telemetry={"curtain_optical_attenuation_db": 6.8},
        )
        result = engine.analyze(req)

        self.assertIsNotNone(result.investigation_id)
        self.assertTrue(result.is_verified)
        matched_ids = [c["case_id"] for c in result.matched_cases]
        self.assertIn("AUDIT-CASE-001", matched_ids)
        self.assertIn("sill", result.root_cause_hypothesis.lower())

        # Verify saved in SQLite repository
        persisted = self.inv_repo.get(result.investigation_id)
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted["status"], "completed")

    def test_scenario_b_csv_telemetry(self):
        """SCENARIO B: CSV telemetry file parsing, validation, and diagnostic integration."""
        csv_file = self.temp_path / "telemetry_test.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["sensor_name", "reading"])
            writer.writerow(["curtain_optical_attenuation_db", "7.2"])
            writer.writerow(["door_cycle_count", "145000"])

        # Parse CSV
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = [r for r in reader if r]
            telemetry = {r[0].strip(): float(r[1].strip()) for r in rows[1:]}

        self.assertIn("curtain_optical_attenuation_db", telemetry)
        self.assertEqual(telemetry["curtain_optical_attenuation_db"], 7.2)

        engine = DiagnosisEngine(
            retrieval_service=self.retrieval_service,
            investigation_repo=self.inv_repo,
            enable_verification=True,
        )
        req = DiagnosisRequest(
            elevator_id="ELV-AUDIT-02",
            subsystem="door_system",
            fault_code="E-DR-201",
            symptoms=["Door dwell buzzer sounding intermittently"],
            telemetry=telemetry,
        )
        result = engine.analyze(req)
        self.assertIsNotNone(result)
        matched_ids = [c["case_id"] for c in result.matched_cases]
        self.assertIn("AUDIT-CASE-001", matched_ids)

    def test_scenario_c_json_fault_data(self):
        """SCENARIO C: Ingest JSON fault record and verify it becomes searchable and retrievable."""
        json_file = self.temp_path / "new_cases.json"
        case_data = [{
            "case_id": "AUDIT-JSON-002",
            "source_title": "Brake Shoe Air-Gap Drag Advisory",
            "source_reference": "OEM-BRK-2024",
            "source_type": "oem_advisory",
            "verification_status": "verified",
            "subsystem": "braking_system",
            "fault_code": "E-BRK-102",
            "symptoms": ["Burning friction smell from machine room", "Brake lift delayed by 450ms"],
            "telemetry_summary": {"brake_solenoid_current_a": 2.1},
            "confirmed_root_cause": "Uneven brake shoe lining wear causing mechanical drum contact.",
            "corrective_action": "Adjust brake shoe air gap to 0.35 mm.",
            "metadata": {"is_synthetic": False},
        }]
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(case_data, f)

        pipeline = FaultCaseIngestionPipeline()
        cases, summary = pipeline.ingest_file(json_file)
        self.assertEqual(len(cases), 1)
        self.assertEqual(summary.valid_records, 1)

        # Save to DB and vector store
        self.case_repo.create(cases[0])
        self.idx_mgr.sync_unindexed_cases(self.case_repo)

        # Retrieve newly added case
        retrieved = self.case_repo.get("AUDIT-JSON-002")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.fault_code, "E-BRK-102")

        # Semantic retrieval
        hits = self.idx_mgr.search("brake shoe friction burning smell", top_k=2)
        top_ids = [h.case_id for h in hits]
        self.assertIn("AUDIT-JSON-002", top_ids)

    def test_scenario_d_insufficient_evidence(self):
        """SCENARIO D: Unfamiliar fault does not invent a confirmed root cause; communicates uncertainty."""
        engine = DiagnosisEngine(
            retrieval_service=self.retrieval_service,
            investigation_repo=self.inv_repo,
            enable_verification=True,
        )
        req = DiagnosisRequest(
            elevator_id="ELV-AUDIT-03",
            subsystem="hydraulic_system",
            fault_code="E-HYD-UNKNOWN",
            symptoms=["Unprecedented ultrasonic hum in oil reservoir during standby"],
            telemetry={"hydraulic_oil_temp_c": 35.0},
        )
        result = engine.analyze(req)
        # Should NOT claim high confidence verified root cause
        self.assertFalse(result.is_verified)
        self.assertIn("inconclusive", result.root_cause_hypothesis.lower())
        persisted = self.inv_repo.get(result.investigation_id)
        self.assertIn(persisted["status"], ("inconclusive", "open", "requires_review"))

    def test_scenario_e_unsupported_diagnosis(self):
        """SCENARIO E: Controlled draft with unsupported claim is rejected by self-verification."""
        engine = DiagnosisEngine(
            retrieval_service=self.retrieval_service,
            investigation_repo=self.inv_repo,
            enable_verification=True,
        )
        # Contradictory scenario: Claims open-circuit coil while telemetry shows 4.2A current
        req = DiagnosisRequest(
            elevator_id="ELV-AUDIT-04",
            subsystem="braking_system",
            fault_code="E-BRK-999",
            symptoms=["Brake does not release; technician suspects open-circuit brake coil"],
            telemetry={"brake_coil_current_a": 4.2},
        )
        result = engine.analyze(req)
        self.assertFalse(result.is_verified)
        self.assertIn("inconclusive", result.verification_record.get("final_status"))

    def test_scenario_f_retry_limit(self):
        """SCENARIO F: Missing evidence respects retry limit (<= 2) and exits with inconclusive status."""
        engine = DiagnosisEngine(
            retrieval_service=self.retrieval_service,
            investigation_repo=self.inv_repo,
            enable_verification=True,
        )
        req = DiagnosisRequest(
            elevator_id="ELV-AUDIT-05",
            subsystem="safety_gear",
            fault_code="E-GOV-901",
            symptoms=["Flyweight governor overspeed tripping on downward run"],
        )
        result = engine.analyze(req)
        # Must enforce bounded retries and not loop indefinitely
        self.assertLessEqual(result.retry_count, 2)
        self.assertFalse(result.is_verified)
        self.assertIn("inconclusive", result.verification_record.get("final_status"))

    def test_scenario_g_provider_failure(self):
        """SCENARIO G: Provider failure engages deterministic fallback transparently."""
        class FailingMockProvider(MockLLMProvider):
            def generate(self, *args, **kwargs):
                raise TimeoutError("External provider connection timed out after 30s")

        engine = DiagnosisEngine(
            retrieval_service=self.retrieval_service,
            investigation_repo=self.inv_repo,
            llm_provider=FailingMockProvider(),
            enable_verification=False,
        )
        req = DiagnosisRequest(
            elevator_id="ELV-AUDIT-06",
            subsystem="door_system",
            fault_code="E-DR-201",
            symptoms=["Car door reopens repeatedly without passenger obstruction"],
        )
        result = engine.analyze(req)
        # Should succeed using deterministic fallback
        self.assertIsNotNone(result)
        self.assertEqual(result.generation_mode, "fallback_deterministic")
        self.assertFalse(result.is_ai_generated)
        self.assertIn("fallback", result.mode_notice.lower())

    def test_scenario_h_persistence(self):
        """SCENARIO H: Saved investigation survives application restart."""
        engine = DiagnosisEngine(
            retrieval_service=self.retrieval_service,
            investigation_repo=self.inv_repo,
            enable_verification=True,
        )
        req = DiagnosisRequest(
            elevator_id="ELV-AUDIT-PERSIST",
            subsystem="door_system",
            fault_code="E-DR-201",
            symptoms=["Car door reopens repeatedly without passenger obstruction"],
        )
        result = engine.analyze(req)
        inv_id = result.investigation_id

        # Simulate complete application restart by instantiating fresh repository from database
        fresh_db = DatabaseManager(self.db_path)
        fresh_inv_repo = InvestigationRepository(fresh_db)
        reloaded = fresh_inv_repo.get(inv_id)

        self.assertIsNotNone(reloaded)
        self.assertEqual(reloaded["elevator_id"], "ELV-AUDIT-PERSIST")
        self.assertEqual(reloaded["fault_code"], "E-DR-201")
        self.assertIn("AUDIT-CASE-001", reloaded["matched_case_ids"])

    def test_scenario_i_knowledge_base_update(self):
        """SCENARIO I: Add fault case, rebuild index, and confirm retrieval without corruption."""
        new_case = FaultCase(
            case_id="AUDIT-UPDATE-003",
            source_title="Traction Sheave Cable Slip Advisory",
            source_reference="OEM-TRC-99",
            source_type="field_report",
            verification_status="verified",
            subsystem="traction_drive",
            fault_code="E-TRC-801",
            symptoms=["Elevator slips during acceleration with half-load"],
            telemetry_summary={"slip_ratio_pct": 8.4},
            confirmed_root_cause="Loss of traction rope groove lubrication and counterweight mismatch.",
            corrective_action="Clean hoist cables, regroove drive sheave, and balance counterweight.",
        )
        self.case_repo.create(new_case)

        # Atomic index rebuild
        self.idx_mgr.rebuild_from_repository(self.case_repo)

        # Verify both old case and new case are retrievable
        status = self.idx_mgr.get_status()
        self.assertEqual(status["total_vectors"], 2)

        results = self.idx_mgr.search("traction sheave cable slip half-load", top_k=2)
        case_ids = [r.case_id for r in results]
        self.assertIn("AUDIT-UPDATE-003", case_ids)

    def test_scenario_j_evaluation(self):
        """SCENARIO J: Run baseline vs self-verifying evaluation pipeline and verify outputs."""
        engine = EvaluationEngine()
        report = engine.run_benchmark()
        self.assertIsNotNone(report.evaluation_id)
        self.assertGreater(report.total_scenarios, 0)
        self.assertGreaterEqual(report.verified_hallucination_rejection_rate, 0.0)
        self.assertLessEqual(report.verified_hallucination_rejection_rate, 1.0)

    def test_scenario_k_ui_workflow(self):
        """SCENARIO K: UI workflow simulation (session state, assistant scoping, Q&A)."""
        engine = DiagnosisEngine(
            retrieval_service=self.retrieval_service,
            investigation_repo=self.inv_repo,
            enable_verification=True,
        )
        req = DiagnosisRequest(
            elevator_id="ELV-AUDIT-UI",
            subsystem="door_system",
            fault_code="E-DR-201",
            symptoms=["Car door reopens repeatedly without passenger obstruction"],
        )
        result = engine.analyze(req)
        inv_data = self.inv_repo.get(result.investigation_id)

        # Test conversational assistant scoped to this session
        assistant = DiagnosticAssistantService()
        resp_grounded = assistant.answer_question(
            investigation=inv_data,
            question="What corrective actions are documented for this door fault?",
        )
        self.assertTrue(resp_grounded["is_supported"])
        self.assertIn("AUDIT-CASE-001", resp_grounded["cited_cases"])

        # Test out-of-domain rejection
        resp_out_of_domain = assistant.answer_question(
            investigation=inv_data,
            question="What is the hydraulic pump pressure?",
        )
        self.assertFalse(resp_out_of_domain["is_supported"])
        self.assertIn("unsupported", resp_out_of_domain["answer"].lower())


if __name__ == "__main__":
    unittest.main()
