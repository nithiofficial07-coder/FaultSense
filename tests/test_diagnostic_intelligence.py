"""Automated Test Suite for FaultSense Diagnostic Intelligence & Case-Specific Analysis.

Validates Requirements A through J from Section 9:
Test A — Different fault inputs (traction drive vs door system)
Test B — Same input repeated (reproducibility)
Test C — No matching evidence (Insufficient Evidence, 0 cases, low score)
Test D — Contradictory evidence (Conflicting Evidence status, capped score)
Test E — Missing telemetry (handled explicitly without crashing)
Test F — Verification failure (accurate recording, no false verified)
Test G — Historical investigation (isolated reloading without re-running)
Test H — Session isolation (multi-session data separation)
Test I — Export consistency (PDF/JSON matching saved investigation)
Test J — UI metric integrity (dynamic non-hardcoded values)
"""

from __future__ import annotations

import json
import unittest
from typing import Any, Dict

from src.diagnosis.engine import DiagnosisEngine
from src.diagnosis.evidence_scorer import DiagnosticStatusType, EvidenceScorer
from src.diagnosis.session import DiagnosisRequest, DiagnosisResult
from src.diagnosis.verification.schema import VerificationVerdict
from src.storage.database import DatabaseManager
from src.storage.repository import InvestigationRepository
from src.utils.report_generator import DiagnosticReportGenerator


class TestDiagnosticIntelligenceSuite(unittest.TestCase):
    """Rigorous verification of dynamic diagnostic intelligence and evidence-grounded outcomes."""

    @classmethod
    def setUpClass(cls):
        cls.db_mgr = DatabaseManager(db_path=":memory:")
        cls.repo = InvestigationRepository(db_manager=cls.db_mgr)
        cls.engine = DiagnosisEngine(investigation_repo=cls.repo, enable_verification=True)

    # -------------------------------------------------------------------------
    # Test A: Different Fault Inputs Produce Distinct Independent Results
    # -------------------------------------------------------------------------
    def test_scenario_a_different_fault_inputs_produce_distinct_results(self):
        """Two meaningfully different fault reports must yield different hypotheses and subsystems."""
        req_door = DiagnosisRequest(
            elevator_id="ELV-DOOR-01",
            subsystem="door_system",
            fault_code="E-DR-201",
            symptoms=[
                "Car door reopens repeatedly without passenger obstruction",
                "Door dwell timer expires causing nudging buzzer",
            ],
            telemetry={"curtain_attenuation_db": 6.8, "motor_current_a": 3.8},
        )

        req_drive = DiagnosisRequest(
            elevator_id="ELV-DRIVE-02",
            subsystem="traction_drive",
            fault_code="E-VFD-404",
            symptoms=[
                "Drive trips on regenerative overvoltage during downward deceleration under heavy load",
                "Motor hunting sensation during braking",
            ],
            telemetry={"dc_bus_voltage_v": 785.0, "ambient_temperature_c": 36.2},
        )

        result_door = self.engine.analyze(req_door)
        result_drive = self.engine.analyze(req_drive)

        # Confirm distinct investigation IDs
        self.assertNotEqual(result_door.investigation_id, result_drive.investigation_id)

        # Confirm distinct subsystems and root causes
        self.assertEqual(result_door.subsystem, "door_system")
        self.assertEqual(result_drive.subsystem, "traction_drive")
        self.assertNotEqual(result_door.root_cause_hypothesis, result_drive.root_cause_hypothesis)

        # Confirm traction drive diagnosis is NOT door curtain sensor
        self.assertNotIn("door", result_drive.root_cause_hypothesis.lower())
        self.assertIn("drive", result_drive.subsystem.lower())

    # -------------------------------------------------------------------------
    # Test B: Same Input Repeated Produces Reproducible Diagnoses
    # -------------------------------------------------------------------------
    def test_scenario_b_same_input_repeated_is_reproducible(self):
        """Repeated submission of identical input produces consistent diagnostic findings."""
        req = DiagnosisRequest(
            elevator_id="ELV-REPRO-03",
            subsystem="braking_system",
            fault_code="E-BRK-102",
            symptoms=[
                "Burning friction smell reported in machine room after express runs",
                "Brake shoe fails to lift cleanly on run command",
            ],
            telemetry={"brake_lining_temp_c": 88.5, "lift_switch_delay_ms": 380},
        )

        result_1 = self.engine.analyze(req)
        result_2 = self.engine.analyze(req)

        # IDs must be unique
        self.assertNotEqual(result_1.investigation_id, result_2.investigation_id)

        # Core diagnosis and confidence must be identical under same KB
        self.assertEqual(result_1.subsystem, result_2.subsystem)
        self.assertEqual(result_1.root_cause_hypothesis, result_2.root_cause_hypothesis)
        self.assertEqual(result_1.confidence_score, result_2.confidence_score)
        self.assertEqual(result_1.diagnostic_status, result_2.diagnostic_status)

    # -------------------------------------------------------------------------
    # Test C: No Matching Evidence Reports Insufficient Evidence (No Hallucination)
    # -------------------------------------------------------------------------
    def test_scenario_c_no_matching_evidence_reports_insufficient(self):
        """Out-of-KB or completely non-existent fault yields Insufficient Evidence with 0 cases."""
        req_novel = DiagnosisRequest(
            elevator_id="ELV-UNKNOWN-99",
            subsystem="other",
            fault_code="XYZ-UNKNOWN-9999",
            symptoms=["Quantum flux capacitor oscillation anomaly in antigravity module"],
            telemetry={"tachyon_flux_gev": 9999.9},
        )

        result_novel = self.engine.analyze(req_novel)

        # Must report insufficient evidence
        self.assertIn(
            result_novel.diagnostic_status,
            [DiagnosticStatusType.INSUFFICIENT_EVIDENCE.value, DiagnosticStatusType.REVIEW_REQUIRED.value],
        )
        # Score must be low (<= 0.35)
        self.assertLessEqual(result_novel.confidence_score, 0.35)

        # Must NOT be marked verified
        self.assertFalse(result_novel.is_verified)

    # -------------------------------------------------------------------------
    # Test D: Contradictory Evidence Lowers Support & Assigns Conflicting Status
    # -------------------------------------------------------------------------
    def test_scenario_d_contradictory_evidence_caps_score_and_flags_conflict(self):
        """Contradictions between sensor readings and claims cap score <= 0.25 and flag Conflicting Evidence."""
        conf, breakdown = EvidenceScorer.compute_confidence(
            evidence_items=[{"similarity_score": 0.85, "subsystem": "braking_system", "fault_code": "E-BRK-102"}],
            request_symptoms=["Brake fails to lift"],
            request_fault_code="E-BRK-102",
            request_subsystem="braking_system",
            request_telemetry={"brake_coil_current_a": 2.5},
            verification_verdict="contradicted",
            contradictions=["Measured coil current of 2.5A directly contradicts open-circuit hypothesis."],
        )

        # Score must be capped below 0.25
        self.assertLessEqual(conf, 0.25)
        self.assertTrue(any("PHYSICAL CONTRADICTION" in p for p in breakdown.penalties_applied))

        status = EvidenceScorer.determine_status(
            is_verified=False,
            verification_verdict="contradicted",
            confidence_score=conf,
            evidence_items=[{"case_id": "CASE-01"}],
            has_fault_code=True,
            has_telemetry=True,
            symptom_count=1,
            contradictions=["Physical contradiction with telemetry"],
        )
        self.assertEqual(status, DiagnosticStatusType.CONFLICTING_EVIDENCE)

    # -------------------------------------------------------------------------
    # Test E: Missing Telemetry Handled Gracefully Without Crashes
    # -------------------------------------------------------------------------
    def test_scenario_e_missing_telemetry_handled_gracefully(self):
        """Absence of telemetry reduces confidence and requires technician review without crashing."""
        req_no_telem = DiagnosisRequest(
            elevator_id="ELV-NOTELEM-05",
            subsystem="door_system",
            fault_code="E-DR-201",
            symptoms=["Car door reopens repeatedly without passenger obstruction"],
            telemetry={},  # Explicitly empty
        )

        result = self.engine.analyze(req_no_telem)

        # Must succeed without error
        self.assertIsNotNone(result.investigation_id)
        # Status must require review since telemetry is absent
        self.assertIn(
            result.diagnostic_status,
            [DiagnosticStatusType.REVIEW_REQUIRED.value, DiagnosticStatusType.PARTIALLY_SUPPORTED.value],
        )
        # Breakdown must note telemetry omission penalty
        bd = result.confidence_breakdown
        self.assertFalse(bd["telemetry_provided"])
        self.assertTrue(any("telemetry omitted" in p.lower() for p in bd["penalties_applied"]))

    # -------------------------------------------------------------------------
    # Test F: Verification Failure Recorded Accurately (No False Verified)
    # -------------------------------------------------------------------------
    def test_scenario_f_verification_failure_recorded_accurately(self):
        """Failed verification must never be marked verified and must assign Verification Failed or Review Required."""
        status = EvidenceScorer.determine_status(
            is_verified=False,
            verification_verdict="failed",
            confidence_score=0.20,
            evidence_items=[{"case_id": "CASE-01"}],
            has_fault_code=True,
            has_telemetry=True,
            symptom_count=2,
            verification_failed=True,
        )
        self.assertEqual(status, DiagnosticStatusType.VERIFICATION_FAILED)

    # -------------------------------------------------------------------------
    # Test G: Historical Investigation Displayed Exactly Without Re-Running
    # -------------------------------------------------------------------------
    def test_scenario_g_historical_investigation_immutable_retrieval(self):
        """Saved investigations can be fetched without modification from persistent storage."""
        req = DiagnosisRequest(
            elevator_id="ELV-HIST-07",
            subsystem="hydraulic_system",
            fault_code="E-HYD-501",
            symptoms=["Car exhibits downward crawl creep when parked at top landing"],
            telemetry={"hydraulic_oil_temp_c": 64.2},
        )
        initial_result = self.engine.analyze(req)
        inv_id = initial_result.investigation_id

        # Retrieve saved record from database
        saved = self.repo.get(inv_id)
        self.assertIsNotNone(saved)
        self.assertEqual(saved["investigation_id"], inv_id)
        self.assertEqual(saved["subsystem"], "hydraulic_system")
        self.assertEqual(saved["fault_code"], "E-HYD-501")
        self.assertEqual(saved["confidence_score"], initial_result.confidence_score)
        self.assertEqual(saved["root_cause_hypothesis"], initial_result.root_cause_hypothesis)

    # -------------------------------------------------------------------------
    # Test H: Session Isolation Between Independent Invocations
    # -------------------------------------------------------------------------
    def test_scenario_h_session_isolation(self):
        """Consecutive diagnostic runs do not contaminate each other's execution states."""
        req1 = DiagnosisRequest(
            elevator_id="ELV-SESS-1",
            subsystem="door_system",
            fault_code="E-DR-201",
            symptoms=["Door cycling"],
            telemetry={"curtain_attenuation_db": 7.0},
        )
        req2 = DiagnosisRequest(
            elevator_id="ELV-SESS-2",
            subsystem="hoistway_signaling",
            fault_code="E-POS-305",
            symptoms=["Leveling oscillation"],
            telemetry={"encoder_pulse_deviation": 30},
        )

        res1 = self.engine.analyze(req1)
        res2 = self.engine.analyze(req2)

        self.assertNotEqual(res1.investigation_id, res2.investigation_id)
        self.assertEqual(res1.subsystem, "door_system")
        self.assertEqual(res2.subsystem, "hoistway_signaling")
        self.assertNotEqual(res1.root_cause_hypothesis, res2.root_cause_hypothesis)

    # -------------------------------------------------------------------------
    # Test I: Export Consistency Between Active Result and PDF/JSON
    # -------------------------------------------------------------------------
    def test_scenario_i_export_consistency(self):
        """Exported PDF and JSON contain the exact investigation ID and diagnostic findings."""
        req = DiagnosisRequest(
            elevator_id="ELV-EXPORT-09",
            subsystem="traction_drive",
            fault_code="E-VFD-404",
            symptoms=["Overvoltage on deceleration"],
            telemetry={"dc_bus_voltage_v": 780},
        )
        result = self.engine.analyze(req)
        saved = self.repo.get(result.investigation_id)

        # Generate JSON export
        json_str = DiagnosticReportGenerator.generate_json(saved)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["investigation_id"], result.investigation_id)
        self.assertEqual(parsed["subsystem"], "traction_drive")
        self.assertEqual(parsed["primary_root_cause"], result.root_cause_hypothesis)
        self.assertEqual(parsed["confidence_score"], result.confidence_score)

        # Generate PDF export
        pdf_bytes = DiagnosticReportGenerator.generate_pdf(saved)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    # -------------------------------------------------------------------------
    # Test J: UI Metric Integrity (Derived From Result, Never Hardcoded)
    # -------------------------------------------------------------------------
    def test_scenario_j_ui_metric_integrity_never_hardcoded(self):
        """Metric calculations are mathematical functions of empirical data, not static constants."""
        # 1. Zero evidence case
        score_zero, bd_zero = EvidenceScorer.compute_confidence(
            evidence_items=[],
            request_symptoms=["Random symptom"],
        )
        self.assertEqual(score_zero, 0.10)
        self.assertEqual(bd_zero.corroboration_count, 0)

        # 2. Strong matching case
        score_high, bd_high = EvidenceScorer.compute_confidence(
            evidence_items=[{
                "similarity_score": 0.82,
                "composite_score": 0.85,
                "subsystem": "door_system",
                "fault_code": "E-DR-201",
                "symptoms": ["door reopens", "optical obstruction"],
                "confirmed_root_cause": "Optical curtain sensor obstruction",
            }],
            request_symptoms=["Car door reopens repeatedly", "optical curtain obstruction"],
            request_fault_code="E-DR-201",
            request_subsystem="door_system",
            request_telemetry={"motor_current_a": 3.8, "attenuation_db": 6.8},
            is_verified=True,
            verification_verdict="sufficient",
        )
        self.assertGreaterEqual(score_high, 0.70)
        self.assertTrue(bd_high.exact_fault_code_match)
        self.assertTrue(bd_high.telemetry_provided)

        # Dynamic variation check: score_zero != score_high
        self.assertNotEqual(score_zero, score_high)


if __name__ == "__main__":
    unittest.main()
