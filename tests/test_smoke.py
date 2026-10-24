"""Startup smoke tests for FaultSense Phase 1 foundation."""

import unittest

from config.settings import get_settings
from src.diagnosis.engine import DiagnosisEngine
from src.diagnosis.session import DiagnosisRequest
from src.evaluation.evaluator import EvaluationEngine
from src.knowledge_base.manager import KnowledgeBaseManager
from src.retrieval.retriever import KeywordRetriever
from src.storage.database import DatabaseManager
from src.storage.repository import FaultCaseRepository, InvestigationRepository
from src.utils.health import HealthChecker


class TestStartupSmoke(unittest.TestCase):
    """End-to-end smoke tests verifying all Phase 1 foundations function in harmony."""

    def setUp(self):
        self.settings = get_settings()

    def test_database_initialization(self):
        """Database manager should initialize tables in SQLite without errors."""
        db = DatabaseManager(db_path=":memory:")
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r[0] for r in cursor.fetchall()]
            self.assertIn("fault_cases", tables)
            self.assertIn("investigations", tables)
        db.close()

    def test_knowledge_base_workflow(self):
        """Knowledge base manager should handle seeding and queries."""
        repo = FaultCaseRepository(db_path=":memory:")
        kb = KnowledgeBaseManager(repository=repo)

        # Initially empty
        stats_initial = kb.get_stats()
        self.assertEqual(stats_initial["total_cases"], 0)

        # Seed sample data
        seeded = kb.seed_initial_data_if_empty()
        self.assertGreater(seeded, 0)

        # Verify query
        cases = kb.search_cases(subsystem="door_system")
        self.assertGreater(len(cases), 0)
        repo.close()

    def test_diagnosis_engine_execution(self):
        """Diagnosis engine should process symptoms, find matches, and record session."""
        repo = FaultCaseRepository(db_path=":memory:")
        kb = KnowledgeBaseManager(repository=repo)
        kb.seed_initial_data_if_empty()

        retriever = KeywordRetriever(repository=repo)
        db_mem = DatabaseManager(db_path=":memory:")
        inv_repo = InvestigationRepository(db_manager=db_mem)

        engine = DiagnosisEngine(retriever=retriever, investigation_repo=inv_repo)

        req = DiagnosisRequest(
            elevator_id="TEST-ELV-99",
            subsystem="door_system",
            fault_code="E-DR-201",
            symptoms=["door reopened", "optical curtain"],
            telemetry={"cycles": 100},
        )

        res = engine.analyze(req)
        self.assertIsNotNone(res.investigation_id)
        self.assertEqual(res.elevator_id, "TEST-ELV-99")
        self.assertGreater(len(res.recommended_actions), 0)
        self.assertGreater(res.confidence_score, 0.0)

        # Verify session logged
        saved_inv = inv_repo.get(res.investigation_id)
        self.assertIsNotNone(saved_inv)
        self.assertEqual(saved_inv["elevator_id"], "TEST-ELV-99")

        repo.close()
        db_mem.close()

    def test_evaluation_engine_placeholder(self):
        """Evaluation engine should return placeholder report with proper phase notice."""
        eval_engine = EvaluationEngine()
        report = eval_engine.run_benchmark()
        self.assertIn("Phase 4", report.status)


if __name__ == "__main__":
    unittest.main()
