"""Test suite for Phase 6 Agentic Self-Verification Loop.

Dual compatible with unittest (run_tests.py) and pytest.
Covers:
- Supported diagnosis finalized
- Unsupported diagnosis rejected
- Contradictory evidence detected
- Successful re-retrieval and refinement
- Maximum retries reached with explicit inconclusive status
- Empty knowledge base handling
- Malformed verification output recovery
- Provider failure during verification
- Prevention of repeated identical retrieval loops
- Audit trail persistence in SQLite
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from fault_sense.repository import FaultCaseRepository
from fault_sense.schema import FaultCase, SourceType, SubsystemType, VerificationStatus
from src.diagnosis.engine import DiagnosisEngine
from src.diagnosis.fallback import DeterministicFallbackEngine
from src.diagnosis.llm import (
    BaseLLMProvider,
    LLMResponse,
    LLMTimeoutError,
    MockLLMProvider,
)
from src.diagnosis.schema import CandidateCause, DiagnosticReport, DiagnosticStatus
from src.diagnosis.session import DiagnosisRequest, DiagnosisResult
from src.diagnosis.verification import (
    AgenticVerificationLoop,
    ClaimStatus,
    ClaimVerification,
    DeterministicEvidenceVerifier,
    DiagnosisVerificationService,
    VerificationRecord,
    VerificationResult,
    VerificationVerdict,
)
from src.retrieval.embeddings import DeterministicEmbeddingGenerator
from src.retrieval.evidence import EvidencePackage, EvidenceSufficiencyLevel
from src.retrieval.index_manager import IndexManager
from src.retrieval.retrieval_service import FaultRetrievalService
from src.retrieval.topology import ElevatorSubsystemTopology
from src.retrieval.vector_store import FAISSVectorStore
from src.storage.database import DatabaseManager
from src.storage.repository import InvestigationRepository


class TestVerificationLoopPhase6(unittest.TestCase):
    """Unit and integration tests for Phase 6 agentic self-verification loop."""

    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="fs_verif_test_"))
        self.idx_dir = self.tmp_dir / "faiss_test"

        self.test_cases = [
            FaultCase(
                case_id="CASE-DOOR-001",
                source_title="Door Interlock Optical Failure",
                source_reference="REF-DR-01",
                source_type=SourceType.FIELD_SERVICE_LOG.value,
                verification_status=VerificationStatus.VERIFIED.value,
                subsystem=SubsystemType.DOOR_SYSTEM.value,
                fault_code="E-DR-201",
                symptoms=["door reopened repeatedly", "optical curtain obstruction light active"],
                telemetry_summary={"curtain_attenuation_db": 6.8, "door_open_cycles": 140000},
                confirmed_root_cause="Particulate contamination in bottom sill guide blocking infrared beam.",
                corrective_action="Vacuumed sill groove and realigned optical curtain emitter.",
            ),
            FaultCase(
                case_id="CASE-TRACTION-002",
                source_title="VVVF Drive Heatsink Thermal Overload",
                source_reference="REF-TR-02",
                source_type=SourceType.OEM_TECHNICAL_BULLETIN.value,
                verification_status=VerificationStatus.VERIFIED.value,
                subsystem=SubsystemType.TRACTION_DRIVE.value,
                fault_code="E-TR-102",
                symptoms=["inverter thermal trip during peak traffic", "drive over-temperature fault"],
                telemetry_summary={"heatsink_temp_c": 88.0, "ambient_room_temp_c": 37.5},
                confirmed_root_cause="Internal cooling fan tachometer failure causing heatsink fan stall.",
                corrective_action="Replaced 24VDC inverter heatsink cooling fan assembly.",
            ),
        ]

        self.repo = FaultCaseRepository(db_path=":memory:")
        self.repo.add(self.test_cases)

        self.embedder = DeterministicEmbeddingGenerator(dimension=384)
        self.vstore = FAISSVectorStore(dimension=384)
        self.vstore.add_cases(self.test_cases, self.embedder)
        self.vstore.save(self.idx_dir)

        self.index_mgr = IndexManager(
            vector_store=self.vstore,
            embedding_generator=self.embedder,
            index_dir=self.idx_dir,
        )

        self.retrieval_service = FaultRetrievalService(
            index_manager=self.index_mgr,
            repository=self.repo,
            topology=ElevatorSubsystemTopology(),
        )

        self.investigation_repo = InvestigationRepository(db_manager=DatabaseManager(":memory:"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_supported_diagnosis_finalized(self) -> None:
        """A well-supported diagnosis is verified on step 1 and finalized."""
        engine = DiagnosisEngine(
            retrieval_service=self.retrieval_service,
            llm_provider=MockLLMProvider(),
            investigation_repo=self.investigation_repo,
            enable_verification=True,
            max_verification_retries=2,
        )

        request = DiagnosisRequest(
            elevator_id="ELV-VERIF-01",
            subsystem="door_system",
            fault_code="E-DR-201",
            symptoms=["door reopened repeatedly"],
            telemetry={"curtain_attenuation_db": 6.8},
        )

        result: DiagnosisResult = engine.analyze(request)

        self.assertTrue(result.is_verified)
        self.assertEqual(result.retry_count, 0)
        self.assertIsNotNone(result.verification_record)
        self.assertEqual(result.verification_record["final_status"], "verified_and_finalized")
        self.assertEqual(result.verification_record["final_verdict"], VerificationVerdict.SUFFICIENT.value)
        self.assertEqual(len(result.verification_record["steps"]), 1)
        self.assertEqual(result.verification_record["steps"][0]["action_taken"], "finalized")

    def test_unsupported_diagnosis_rejected(self) -> None:
        """A draft containing unsupported hallucinated claims is rejected by verification."""
        # Provider returns a claim asserting an ungrounded component failure
        unsupported_json = {
            "summary": "Hydraulic valve failure analysis.",
            "candidate_causes": [
                {
                    "rank": 1,
                    "hypothesis_title": "Hydraulic proportional valve seal rupture",
                    "subsystem": "hydraulic_system",
                    "probability_band": "likely",
                    "explanation": "High pressure oil leakage through bypass check valve.",
                    "supporting_case_ids": ["CASE-DOOR-001"],  # Cited case is actually a door case, not hydraulic
                    "conflicting_evidence": [],
                    "recommended_checks": ["Inspect oil reservoir"],
                    "documented_corrective_actions": ["Replace valve assembly"],
                }
            ],
            "confidence_score": 0.90,
        }

        mock_provider = MockLLMProvider(fixed_response=json.dumps(unsupported_json))
        engine = DiagnosisEngine(
            retrieval_service=self.retrieval_service,
            llm_provider=mock_provider,
            investigation_repo=self.investigation_repo,
            enable_verification=True,
            max_verification_retries=1,
        )

        request = DiagnosisRequest(
            elevator_id="ELV-VERIF-02",
            subsystem="door_system",
            fault_code="E-DR-201",
            symptoms=["door reopened repeatedly"],
        )

        result: DiagnosisResult = engine.analyze(request)

        # Verification must reject unsupported draft and return inconclusive status
        self.assertFalse(result.is_verified)
        self.assertEqual(result.diagnostic_report["status"], DiagnosticStatus.INCONCLUSIVE.value)
        self.assertIn("INCONCLUSIVE", result.diagnostic_report["summary"])
        self.assertGreater(len(result.diagnostic_report["uncertainty_and_missing_info"]), 0)

    def test_contradictory_evidence_detected(self) -> None:
        """Evidence verifier flags direct contradictions between candidate causes and evidence."""
        evidence = self.retrieval_service.retrieve_evidence(
            symptoms=["door reopened repeatedly"],
            subsystem="door_system",
        )

        # Create draft asserting contradictory subsystem
        contradictory_report = DiagnosticReport(
            investigation_id="INV-TEST-CONTRA",
            elevator_id="ELV-99",
            subsystem="door_system",
            fault_code="E-DR-201",
            status=DiagnosticStatus.COMPLETED.value,
            summary="Contradictory claim report.",
            candidate_causes=[
                CandidateCause(
                    rank=1,
                    hypothesis_title="Hydraulic cylinder seal rupture",
                    subsystem="hydraulic_system",  # Contradicts door_system
                    probability_band="likely",
                    explanation="Cylinder oil bypass causing floor slip.",
                    supporting_case_ids=["CASE-DOOR-001"],
                )
            ],
        )

        request = DiagnosisRequest(
            elevator_id="ELV-99",
            subsystem="door_system",
            symptoms=["door reopened repeatedly"],
        )

        verif_result: VerificationResult = DeterministicEvidenceVerifier.verify(
            contradictory_report, evidence, request
        )

        self.assertFalse(verif_result.is_verified)
        self.assertEqual(verif_result.verdict, VerificationVerdict.CONTRADICTED.value)
        self.assertGreater(verif_result.contradicted_count, 0)
        self.assertGreater(len(verif_result.claims[0].contradictions), 0)

    def test_successful_re_retrieval(self) -> None:
        """When initial retrieval lacks evidence, query refinement and expanded top_k succeed on retry."""
        # Step 1 verifier fails initially due to top_k=1 (no code match), then succeeds when top_k expands
        call_count = 0

        class DynamicMockVerifier(DiagnosisVerificationService):
            def verify(self, report, evidence, request):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First attempt fails with missing evidence
                    return VerificationResult(
                        verdict=VerificationVerdict.INSUFFICIENT.value,
                        is_verified=False,
                        verified_by="test_dynamic_verifier",
                        claims=[
                            ClaimVerification(
                                claim_text="Optical obstruction",
                                status=ClaimStatus.PARTIALLY_SUPPORTED.value,
                                missing_evidence_notes="Need more cases with exact DTC match",
                            )
                        ],
                        supported_count=0,
                        partially_supported_count=1,
                        unsupported_count=1,
                        missing_evidence_reasons=["Initial top-1 retrieval lacked corroborating cases."],
                        suggested_query_refinements=["sill", "optical"],
                    )
                else:
                    # Second attempt succeeds after re-retrieval
                    return VerificationResult(
                        verdict=VerificationVerdict.SUFFICIENT.value,
                        is_verified=True,
                        verified_by="test_dynamic_verifier",
                        claims=[
                            ClaimVerification(
                                claim_text="Optical obstruction",
                                status=ClaimStatus.SUPPORTED.value,
                                cited_case_ids=["CASE-DOOR-001"],
                            )
                        ],
                        supported_count=1,
                    )

        dynamic_verifier = DynamicMockVerifier(force_fallback=True)
        engine = DiagnosisEngine(
            retrieval_service=self.retrieval_service,
            llm_provider=MockLLMProvider(),
            verification_service=dynamic_verifier,
            investigation_repo=self.investigation_repo,
            enable_verification=True,
            max_verification_retries=2,
        )

        request = DiagnosisRequest(
            elevator_id="ELV-VERIF-04",
            subsystem="door_system",
            fault_code="E-DR-201",
            symptoms=["door reopened repeatedly"],
        )

        result = engine.analyze(request)

        self.assertTrue(result.is_verified)
        self.assertEqual(result.retry_count, 1)  # Succeeded on retry 1
        self.assertEqual(len(result.verification_record["steps"]), 2)
        self.assertEqual(result.verification_record["steps"][0]["action_taken"], "re_retrieval_initiated")
        self.assertEqual(result.verification_record["steps"][1]["action_taken"], "finalized")

    def test_maximum_retries_reached(self) -> None:
        """When retries are exhausted, an explicit inconclusive status is returned, never silently approved."""
        class AlwaysInsufficientVerifier(DiagnosisVerificationService):
            def verify(self, report, evidence, request):
                return VerificationResult(
                    verdict=VerificationVerdict.INSUFFICIENT.value,
                    is_verified=False,
                    verified_by="always_insufficient_verifier",
                    claims=[
                        ClaimVerification(
                            claim_text="Unknown failure",
                            status=ClaimStatus.UNSUPPORTED.value,
                            missing_evidence_notes="Telemetry does not corroborate claim.",
                        )
                    ],
                    unsupported_count=1,
                    missing_evidence_reasons=["No matching OEM bulletins found for this combination."],
                    suggested_query_refinements=["wiring", "relay"],
                )

        engine = DiagnosisEngine(
            retrieval_service=self.retrieval_service,
            verification_service=AlwaysInsufficientVerifier(force_fallback=True),
            investigation_repo=self.investigation_repo,
            enable_verification=True,
            max_verification_retries=2,
        )

        request = DiagnosisRequest(
            elevator_id="ELV-VERIF-05",
            subsystem="door_system",
            fault_code="E-DR-201",
            symptoms=["unusual humming noise"],
        )

        result = engine.analyze(request)

        self.assertFalse(result.is_verified)
        self.assertEqual(result.retry_count, 2)
        self.assertEqual(result.verification_record["final_status"], "inconclusive_max_retries")
        self.assertEqual(result.diagnostic_report["status"], DiagnosticStatus.INCONCLUSIVE.value)
        # Ensure recommended checks are provided
        self.assertGreater(len(result.recommended_actions), 0)

    def test_empty_knowledge_base_handling(self) -> None:
        """When knowledge base has 0 cases, verification immediately handles as inconclusive."""
        empty_tmp = Path(tempfile.mkdtemp(prefix="fs_empty_kb_"))
        empty_vs = FAISSVectorStore(dimension=384)
        empty_idx_mgr = IndexManager(
            vector_store=empty_vs,
            embedding_generator=self.embedder,
            index_dir=empty_tmp,
        )
        empty_repo = FaultCaseRepository(db_path=":memory:")
        empty_retrieval_svc = FaultRetrievalService(
            index_manager=empty_idx_mgr,
            repository=empty_repo,
        )

        engine = DiagnosisEngine(
            retrieval_service=empty_retrieval_svc,
            investigation_repo=self.investigation_repo,
            enable_verification=True,
            max_verification_retries=1,
        )

        request = DiagnosisRequest(
            elevator_id="ELV-EMPTY-01",
            subsystem="door_system",
            symptoms=["door reopened"],
        )

        result = engine.analyze(request)

        self.assertFalse(result.is_verified)
        self.assertEqual(result.diagnostic_report["status"], DiagnosticStatus.INCONCLUSIVE.value)
        shutil.rmtree(empty_tmp, ignore_errors=True)

    def test_malformed_verification_output(self) -> None:
        """Malformed JSON from verification LLM engages deterministic verifier without throwing."""
        class MalformedVerificationLLM(MockLLMProvider):
            def generate(self, prompt, system_prompt=None, temperature=0.2, max_tokens=1500):
                return LLMResponse(
                    content="<<< NOT A JSON OBJECT >>>",
                    provider="malformed_llm",
                    model="mock",
                )

        verif_svc = DiagnosisVerificationService(llm_provider=MalformedVerificationLLM())
        evidence = self.retrieval_service.retrieve_evidence(
            symptoms=["door reopened repeatedly"],
            subsystem="door_system",
        )
        draft = DeterministicFallbackEngine.generate_report(
            request=DiagnosisRequest(elevator_id="E1", subsystem="door_system", symptoms=["door reopened"]),
            evidence=evidence,
            investigation_id="INV-MALFORMED",
        )

        # Verification must catch JSONDecodeError and safely return deterministic fallback
        result = verif_svc.verify(
            report=draft,
            evidence=evidence,
            request=DiagnosisRequest(elevator_id="E1", subsystem="door_system", symptoms=["door reopened"]),
        )

        self.assertIsNotNone(result)
        self.assertTrue(result.is_fallback)
        self.assertIn("Deterministic Verification Notice", result.limitations_notice)

    def test_provider_failure_during_verification(self) -> None:
        """Provider timeout during verification engages deterministic verification fallback."""
        class TimeoutVerificationLLM(MockLLMProvider):
            def generate(self, prompt, system_prompt=None, temperature=0.2, max_tokens=1500):
                raise LLMTimeoutError("Verification LLM request timed out after 30s")

        verif_svc = DiagnosisVerificationService(llm_provider=TimeoutVerificationLLM())
        evidence = self.retrieval_service.retrieve_evidence(
            symptoms=["door reopened repeatedly"],
            subsystem="door_system",
        )
        draft = DeterministicFallbackEngine.generate_report(
            request=DiagnosisRequest(elevator_id="E2", subsystem="door_system", symptoms=["door reopened"]),
            evidence=evidence,
            investigation_id="INV-TIMEOUT",
        )

        result = verif_svc.verify(
            report=draft,
            evidence=evidence,
            request=DiagnosisRequest(elevator_id="E2", subsystem="door_system", symptoms=["door reopened"]),
        )

        self.assertIsNotNone(result)
        self.assertTrue(result.is_fallback)
        self.assertIn("LLM Verifier Exception", result.notes)

    def test_loop_prevents_repeated_identical_retrieval(self) -> None:
        """Loop detects identical query signatures to prevent infinite cycling."""
        loop = AgenticVerificationLoop(
            retrieval_service=self.retrieval_service,
            verification_service=DiagnosisVerificationService(force_fallback=True),
            max_retries=5,  # High retry limit
            force_fallback=True,
        )

        request = DiagnosisRequest(
            elevator_id="ELV-CYCLE-01",
            subsystem="door_system",
            fault_code="E-DR-201",
            symptoms=["door reopened repeatedly"],
        )

        report, evidence, record = loop.execute(request, investigation_id="INV-CYCLE-01")

        # Must exit before exhausting 5 retries because query cannot produce new cases
        self.assertLessEqual(record.total_retries, 2)

    def test_verification_audit_trail_persisted_in_sqlite(self) -> None:
        """Full verification record and retry steps are persisted into SQLite and retrievable."""
        engine = DiagnosisEngine(
            retrieval_service=self.retrieval_service,
            llm_provider=MockLLMProvider(),
            investigation_repo=self.investigation_repo,
            enable_verification=True,
            max_verification_retries=2,
        )

        request = DiagnosisRequest(
            elevator_id="ELV-PERSIST-01",
            subsystem="door_system",
            fault_code="E-DR-201",
            symptoms=["door reopened repeatedly"],
        )

        result = engine.analyze(request)
        inv_id = result.investigation_id

        # Query database directly
        persisted = self.investigation_repo.get(inv_id)
        self.assertIsNotNone(persisted)
        self.assertIn("verification_record", persisted)
        self.assertEqual(persisted["status"], "completed")
        self.assertEqual(persisted["retry_count"], 0)
        self.assertEqual(persisted["verification_record"]["final_status"], "verified_and_finalized")


if __name__ == "__main__":
    unittest.main()
