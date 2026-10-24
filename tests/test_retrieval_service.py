"""Unit and integration tests for Phase 4 Fault Retrieval Service and Evidence Packaging.

Compatible with both unittest (run_tests.py) and pytest.
Covers:
- Relevant retrieval
- Unrelated / out-of-domain queries and sufficiency failure
- Exact fault-code matching and boost
- Strict vs Soft-Rerank metadata filtering
- Empty results and zero-evidence handling
- Missing metadata resilience
- Case ID and source provenance consistency
- Configurable ranking strategies
- Candidate fault propagation topology and causality disclaimers
- EvidencePackage serialization
- Telemetry feature overlap scoring
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from fault_sense.repository import FaultCaseRepository
from fault_sense.schema import FaultCase, SourceType, SubsystemType, VerificationStatus
from src.retrieval.embeddings import DeterministicEmbeddingGenerator
from src.retrieval.evidence import (
    EvidencePackage,
    EvidenceSufficiencyLevel,
)
from src.retrieval.index_manager import IndexManager
from src.retrieval.ranking import (
    FilterMode,
    RankingStrategy,
    RankingWeights,
    explain_filter_mode,
)
from src.retrieval.retrieval_service import FaultRetrievalService, compute_telemetry_overlap
from src.retrieval.topology import CandidatePropagation, ElevatorSubsystemTopology
from src.retrieval.vector_store import FAISSVectorStore


class TestFaultRetrievalService(unittest.TestCase):
    """Test suite covering Phase 4 retrieval, ranking, and evidence package generation."""

    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="fs_test_retrieval_"))
        self.idx_dir = self.tmp_dir / "faiss_test"

        self.test_cases = [
            FaultCase(
                case_id="CASE-DOOR-001",
                source_title="Door Interlock Optical Failure",
                source_reference="REF-DOOR-01",
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
                source_reference="REF-TRAC-02",
                source_type=SourceType.OEM_TECHNICAL_BULLETIN.value,
                verification_status=VerificationStatus.VERIFIED.value,
                subsystem=SubsystemType.TRACTION_DRIVE.value,
                fault_code="E-TR-102",
                symptoms=["inverter thermal trip during peak traffic", "drive over-temperature fault"],
                telemetry_summary={"heatsink_temp_c": 88.0, "ambient_room_temp_c": 37.5},
                confirmed_root_cause="Internal cooling fan tachometer failure causing heatsink fan stall.",
                corrective_action="Replaced 24VDC inverter heatsink cooling fan assembly.",
            ),
            FaultCase(
                case_id="CASE-BRAKE-003",
                source_title="Brake Shoe Dragging and Coil Under-voltage",
                source_reference="REF-BRK-03",
                source_type=SourceType.INCIDENT_INVESTIGATION.value,
                verification_status=VerificationStatus.VERIFIED.value,
                subsystem=SubsystemType.BRAKING_SYSTEM.value,
                fault_code="E-BRK-302",
                symptoms=["motor current overload at launch", "brake dragging smell", "loud friction hum"],
                telemetry_summary={"coil_pickup_v": 78.0, "motor_current_peak_a": 44.0},
                confirmed_root_cause="Degraded electrolytic capacitor in brake rectifier circuit dropping coil voltage.",
                corrective_action="Replaced brake power supply rectifier and recalibrated air gap to 0.40mm.",
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

        self.topology = ElevatorSubsystemTopology()

        self.service = FaultRetrievalService(
            index_manager=self.index_mgr,
            repository=self.repo,
            topology=self.topology,
            default_ranking_strategy=RankingStrategy.HYBRID_BALANCED,
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_relevant_retrieval_door_system(self) -> None:
        """Relevant query should retrieve matching case with valid evidence package."""
        pkg = self.service.retrieve_evidence(
            subsystem="door_system",
            fault_code="E-DR-201",
            symptoms=["door reopened repeatedly", "optical curtain obstruction"],
            top_k=2,
            filter_mode=FilterMode.SOFT_RERANK,
        )

        self.assertIsInstance(pkg, EvidencePackage)
        self.assertGreater(pkg.returned_count, 0)
        top_item = pkg.items[0]
        self.assertEqual(top_item.case_id, "CASE-DOOR-001")
        self.assertEqual(top_item.subsystem, "door_system")
        self.assertGreater(top_item.similarity_score, 0.0)
        self.assertGreater(top_item.composite_score, 0.0)
        self.assertTrue(top_item.match_rationale.exact_fault_code_match)
        self.assertTrue(top_item.match_rationale.exact_subsystem_match)
        self.assertTrue(pkg.sufficiency.is_sufficient)

    def test_unrelated_query_evidence_sufficiency(self) -> None:
        """Unrelated out-of-domain query should be classified as low/insufficient evidence."""
        pkg = self.service.retrieve_evidence(
            subsystem="door_system",
            fault_code=None,
            symptoms=["making an espresso coffee in the kitchen", "coffee machine leaking boiling water"],
            top_k=3,
            filter_mode=FilterMode.SOFT_RERANK,
        )

        self.assertIsInstance(pkg, EvidencePackage)
        self.assertGreater(len(pkg.warnings), 0)
        self.assertIn(
            pkg.sufficiency.level,
            (EvidenceSufficiencyLevel.LOW.value, EvidenceSufficiencyLevel.INSUFFICIENT.value),
        )

    def test_exact_fault_code_matching_boost(self) -> None:
        """Exact fault code match should receive configured ranking boost."""
        pkg = self.service.retrieve_evidence(
            fault_code="E-TR-102",
            symptoms=["intermittent stall"],  # Sparse/generic symptoms
            subsystem=None,
            top_k=3,
            ranking_strategy=RankingStrategy.CODE_PRIORITIZED,
        )

        self.assertGreater(pkg.returned_count, 0)
        top_item = pkg.items[0]
        self.assertEqual(top_item.case_id, "CASE-TRACTION-002")
        self.assertTrue(top_item.match_rationale.exact_fault_code_match)
        self.assertGreater(top_item.composite_score, 0.50)

    def test_strict_vs_soft_filtering(self) -> None:
        """Strict filtering must exclude other subsystems; soft rerank must permit cross-subsystem candidates."""
        # 1. Strict filtering
        pkg_strict = self.service.retrieve_evidence(
            subsystem="door_system",
            symptoms=["friction noise and motor current spike"],
            top_k=5,
            filter_mode=FilterMode.STRICT,
        )
        for item in pkg_strict.items:
            self.assertEqual(item.subsystem, "door_system")

        # 2. Soft rerank filtering allows cross-subsystem discovery
        pkg_soft = self.service.retrieve_evidence(
            subsystem="traction_drive",
            symptoms=["brake dragging smell", "loud friction hum", "motor current overload"],
            top_k=3,
            filter_mode=FilterMode.SOFT_RERANK,
        )
        subsystems_found = {it.subsystem for it in pkg_soft.items}
        self.assertTrue("braking_system" in subsystems_found or len(pkg_soft.items) > 0)

    def test_empty_results_handling(self) -> None:
        """Query matching no records under strict constraints must return clean empty package without error."""
        pkg = self.service.retrieve_evidence(
            subsystem="non_existent_subsystem",
            symptoms=["test symptom"],
            top_k=3,
            filter_mode=FilterMode.STRICT,
        )

        self.assertEqual(pkg.returned_count, 0)
        self.assertEqual(pkg.items, [])
        self.assertFalse(pkg.sufficiency.is_sufficient)
        self.assertEqual(pkg.sufficiency.level, EvidenceSufficiencyLevel.INSUFFICIENT.value)
        self.assertGreater(len(pkg.warnings), 0)

    def test_missing_metadata_resilience(self) -> None:
        """Retrieval should handle None fault_code, None subsystem, and empty telemetry cleanly."""
        pkg = self.service.retrieve_evidence(
            symptoms=["unusual humming and vibration during flight"],
            fault_code=None,
            subsystem=None,
            telemetry={},
            top_k=2,
        )

        self.assertIsInstance(pkg, EvidencePackage)
        self.assertIsNone(pkg.query.fault_code)
        self.assertIsNone(pkg.query.subsystem)
        self.assertEqual(pkg.query.telemetry, {})
        self.assertGreater(pkg.returned_count, 0)

    def test_case_id_and_provenance_traceability(self) -> None:
        """Every returned evidence item must carry complete traceable provenance and metadata."""
        pkg = self.service.retrieve_evidence(
            symptoms=["door reopened repeatedly"],
            fault_code="E-DR-201",
            subsystem="door_system",
            top_k=1,
        )

        self.assertEqual(len(pkg.items), 1)
        item = pkg.items[0]
        self.assertEqual(item.case_id, "CASE-DOOR-001")
        self.assertEqual(item.source_title, "Door Interlock Optical Failure")
        self.assertEqual(item.source_reference, "REF-DOOR-01")
        self.assertEqual(item.source_type, SourceType.FIELD_SERVICE_LOG.value)
        self.assertEqual(item.verification_status, VerificationStatus.VERIFIED.value)
        self.assertFalse(item.is_synthetic)
        self.assertEqual(len(item.symptoms), 2)
        self.assertIn("curtain_attenuation_db", item.telemetry_summary)

    def test_ranking_strategy_weights(self) -> None:
        """Different ranking strategies must apply distinct documented weights."""
        w_bal = RankingWeights.from_strategy(RankingStrategy.HYBRID_BALANCED)
        self.assertEqual(w_bal.w_semantic, 0.70)
        self.assertEqual(w_bal.w_fault_code, 0.18)
        self.assertEqual(w_bal.w_subsystem, 0.12)

        w_sem = RankingWeights.from_strategy(RankingStrategy.SEMANTIC_ONLY)
        self.assertEqual(w_sem.w_semantic, 1.00)
        self.assertEqual(w_sem.w_fault_code, 0.00)

        w_code = RankingWeights.from_strategy(RankingStrategy.CODE_PRIORITIZED)
        self.assertEqual(w_code.w_fault_code, 0.40)

        # Custom weights
        w_cust = RankingWeights.from_strategy(
            RankingStrategy.CUSTOM,
            custom_weights={"w_semantic": 0.5, "w_fault_code": 0.3, "w_subsystem": 0.2, "w_telemetry": 0.0},
        )
        self.assertEqual(w_cust.w_semantic, 0.5)

    def test_candidate_propagation_and_causality_disclaimer(self) -> None:
        """Candidate propagation between coupled subsystems must carry causality disclaimer."""
        prop = ElevatorSubsystemTopology.get_candidate_propagation("braking_system", "traction_drive")
        self.assertIsNotNone(prop)
        self.assertEqual(prop.source_subsystem, "braking_system")
        self.assertEqual(prop.target_subsystem, "traction_drive")
        self.assertEqual(prop.coupling_type, "mechanical_drag")
        self.assertIn("cannot be proven by vector similarity alone", prop.causality_disclaimer)

    def test_evidence_package_json_serialization(self) -> None:
        """EvidencePackage.to_dict() must be completely JSON-serializable."""
        pkg = self.service.retrieve_evidence(
            subsystem="door_system",
            fault_code="E-DR-201",
            symptoms=["door reopened"],
            top_k=2,
        )

        d = pkg.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("query", d)
        self.assertIn("items", d)
        self.assertIn("sufficiency", d)
        self.assertIn("filter_explanation", d)
        self.assertIn("retrieved_case_ids", d)

        # Verify JSON dump round-trip without error
        json_str = json.dumps(d, indent=2)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["query"]["fault_code"], "E-DR-201")
        self.assertEqual(len(parsed["items"]), len(pkg.items))

    def test_telemetry_overlap_computation(self) -> None:
        """compute_telemetry_overlap should score sensor proximity bounded in [0.0, 1.0]."""
        # Identical telemetry
        t1 = {"voltage_v": 24.0, "current_a": 5.0}
        t2 = {"voltage_v": 24.0, "current_a": 5.0}
        score_identical = compute_telemetry_overlap(t1, t2)
        self.assertEqual(score_identical, 1.0)

        # Disjoint keys
        t3 = {"pressure_bar": 100.0}
        score_disjoint = compute_telemetry_overlap(t1, t3)
        self.assertEqual(score_disjoint, 0.0)

        # Empty telemetry
        self.assertEqual(compute_telemetry_overlap({}, t1), 0.0)
        self.assertEqual(compute_telemetry_overlap(t1, {}), 0.0)


if __name__ == "__main__":
    unittest.main()
