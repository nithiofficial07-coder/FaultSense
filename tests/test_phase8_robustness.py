"""Robustness and final validation test suite for FaultSense Phase 8."""

import json
import unittest

from config.settings import get_settings
from fault_sense.repository import FaultCaseRepository
from fault_sense.schema import FaultCase, SubsystemType
from src.diagnosis.engine import DiagnosisEngine
from src.diagnosis.llm.base import BaseLLMProvider
from src.diagnosis.llm.providers import LLMError, LLMTimeoutError, MockLLMProvider, mask_credential
from src.diagnosis.session import DiagnosisRequest
from src.retrieval.vector_store import FAISSVectorStore
from src.storage.database import DatabaseManager
from src.storage.repository import InvestigationRepository


class ExplodingVerificationLLM(MockLLMProvider):
    """Simulates an LLM provider that throws network / rate-limit exceptions."""

    def generate(self, prompt: str, system_instruction: str = "", **kwargs) -> str:
        raise LLMError("Rate limit exceeded (HTTP 429: Too Many Requests)")


class CorruptJSONVerificationLLM(MockLLMProvider):
    """Simulates an LLM provider emitting malformed non-JSON text."""

    def generate(self, prompt: str, system_instruction: str = "", **kwargs) -> str:
        return "I think the fault is definitely the door interlock, but I won't output JSON!"


class TestPhase8Robustness(unittest.TestCase):
    """Validates resilience against provider failures, malformed data, and retry limits."""

    def setUp(self):
        self.db_mgr = DatabaseManager(db_path=":memory:")
        self.inv_repo = InvestigationRepository(db_manager=self.db_mgr)
        self.case_repo = FaultCaseRepository(db_path=":memory:")
        self.vector_store = FAISSVectorStore(dimension=384)

        # Seed sample case
        self.case_repo.add(
            FaultCase(
                case_id="CASE-SYNTH-ELEV-001",
                source_title="Illustrative Engineering Benchmark: Optical Curtain Obstruction",
                source_reference="FAULT-SENSE-SYNTH-BENCH-2024-01",
                source_type="synthetic_illustrative",
                verification_status="unverified",
                subsystem=SubsystemType.DOOR_SYSTEM.value,
                fault_code="E-DR-201",
                symptoms=["Car door reopens repeatedly without passenger obstruction"],
                telemetry_summary={"curtain_optical_attenuation_db": 6.8},
                confirmed_root_cause="Grit in bottom sill guide track.",
                corrective_action="Vacuum and clean sill track grooves.",
                metadata={"is_synthetic": True},
            )
        )

    def test_credential_masking_security(self):
        """API credentials are sanitized and never exposed in plaintext."""
        self.assertEqual(mask_credential(""), "[NOT CONFIGURED]")
        self.assertEqual(mask_credential("short"), "***")
        masked = mask_credential("sk-proj-1234567890abcdef1234567890")
        self.assertTrue(masked.startswith("sk-p"))
        self.assertTrue(masked.endswith("7890"))
        self.assertIn("...", masked)
        self.assertNotIn("abcdef", masked)

    def test_synthetic_records_labeled_clearly(self):
        """Illustrative records are strictly flagged with is_synthetic metadata."""
        case = self.case_repo.get("CASE-SYNTH-ELEV-001")
        self.assertIsNotNone(case)
        self.assertTrue(case.is_synthetic)
        self.assertEqual(case.source_type, "synthetic_illustrative")
        self.assertEqual(case.verification_status, "unverified")

    def test_llm_rate_limit_failure_engages_deterministic_fallback(self):
        """Provider rate-limit or network failure engages deterministic fallback seamlessly."""
        engine = DiagnosisEngine(
            llm_provider=ExplodingVerificationLLM(),
            enable_verification=True,
            investigation_repo=self.inv_repo,
        )
        req = DiagnosisRequest(
            elevator_id="ELV-FAIL-01",
            subsystem="door_system",
            fault_code="E-DR-201",
            symptoms=["Car door reopens repeatedly without passenger obstruction"],
        )
        res = engine.analyze(req)
        self.assertIsNotNone(res)
        self.assertIn("fallback", res.generation_mode.lower())

    def test_malformed_llm_json_handled_gracefully(self):
        """Malformed non-JSON output from LLM engages deterministic verification."""
        engine = DiagnosisEngine(
            llm_provider=CorruptJSONVerificationLLM(),
            enable_verification=True,
            investigation_repo=self.inv_repo,
        )
        req = DiagnosisRequest(
            elevator_id="ELV-MALFORM-01",
            subsystem="door_system",
            fault_code="E-DR-201",
            symptoms=["Car door reopens repeatedly without passenger obstruction"],
        )
        res = engine.analyze(req)
        self.assertIsNotNone(res)
        self.assertIsNotNone(res.root_cause_hypothesis)

    def test_unsupported_out_of_kb_scenario_bounded_and_inconclusive(self):
        """Novel out-of-domain scenario terminates at max retries with inconclusive status."""
        engine = DiagnosisEngine(
            enable_verification=True,
            investigation_repo=self.inv_repo,
        )
        req = DiagnosisRequest(
            elevator_id="ELV-UNSEEN-01",
            subsystem="safety_gear",
            fault_code="E-GOV-901",
            symptoms=["Flyweight overspeed governor trip wedges car into hoistway rails"],
        )
        res = engine.analyze(req)
        self.assertFalse(res.is_verified)
        self.assertIn("inconclusive", res.generation_mode.lower())
        self.assertEqual(res.retry_count, engine.settings.max_verification_retries)
        self.assertIn("INCONCLUSIVE", res.root_cause_hypothesis)
        self.assertGreater(len(res.recommended_actions), 0)


if __name__ == "__main__":
    unittest.main()
