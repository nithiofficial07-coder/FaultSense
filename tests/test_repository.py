"""Unit tests for the FaultCase SQLite Knowledge Base repository."""

import json
from pathlib import Path
import tempfile
import unittest

from fault_sense.repository import DuplicateCaseError, FaultCaseRepository
from fault_sense.schema import FaultCase


class TestFaultCaseRepository(unittest.TestCase):
    """Tests SQLite persistence, search, CRUD operations, and exports."""

    def setUp(self):
        # Use in-memory SQLite database for test isolation
        self.repo = FaultCaseRepository(db_path=":memory:", enable_fts=True)

        self.case_1 = FaultCase(
            case_id="CASE-ELEV-001",
            source_title="Field Log #01",
            source_reference="REF-001",
            source_type="field_service_log",
            verification_status="verified",
            subsystem="door_system",
            fault_code="E-DR-101",
            symptoms=["Door reopened 3 times", "Nudging active"],
            telemetry_summary={"door_cycles": 12000, "motor_temp_c": 50.1},
            confirmed_root_cause="Debris in bottom sill groove",
            corrective_action="Cleaned track and re-calibrated sensors",
            timestamp="2024-10-01T08:00:00Z",
            metadata={"is_synthetic": False, "building": "HQ"},
        )

        self.case_2 = FaultCase(
            case_id="CASE-ELEV-002",
            source_title="Field Log #02",
            source_reference="REF-002",
            source_type="synthetic_illustrative",
            verification_status="unverified",
            subsystem="traction_drive",
            fault_code="E-VFD-202",
            symptoms=["Vibration during descent", "High DC bus voltage"],
            telemetry_summary={"dc_bus_v": 780.0, "vibration_g": 0.42},
            confirmed_root_cause="Regenerative chopper transistor failure",
            corrective_action="Replaced brake chopper module",
            timestamp="2024-10-02T09:00:00Z",
            metadata={"is_synthetic": True, "building": "Tower B"},
        )

    def test_add_and_get(self):
        """Should persist and retrieve a FaultCase accurately."""
        count = self.repo.add(self.case_1)
        self.assertEqual(count, 1)

        retrieved = self.repo.get("CASE-ELEV-001")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.case_id, "CASE-ELEV-001")
        self.assertEqual(retrieved.subsystem, "door_system")
        self.assertEqual(retrieved.symptoms, ["Door reopened 3 times", "Nudging active"])
        self.assertEqual(retrieved.telemetry_summary["motor_temp_c"], 50.1)

    def test_duplicate_case_rejected_by_default(self):
        """Adding a duplicate case_id with allow_update=False must raise DuplicateCaseError."""
        self.repo.add(self.case_1)
        with self.assertRaises(DuplicateCaseError):
            self.repo.add(self.case_1, allow_update=False)

    def test_add_with_allow_update_overwrites(self):
        """Adding a duplicate case_id with allow_update=True should update the record."""
        self.repo.add(self.case_1)
        modified = FaultCase.from_dict(self.case_1.to_dict())
        modified.corrective_action = "Updated action: replaced complete sill"

        self.repo.add(modified, allow_update=True)
        retrieved = self.repo.get("CASE-ELEV-001")
        self.assertEqual(retrieved.corrective_action, "Updated action: replaced complete sill")

    def test_search_by_subsystem_and_status(self):
        """Should filter cases by subsystem and verification status."""
        self.repo.add([self.case_1, self.case_2])

        door_cases = self.repo.search(subsystem="door_system")
        self.assertEqual(len(door_cases), 1)
        self.assertEqual(door_cases[0].case_id, "CASE-ELEV-001")

        verified_cases = self.repo.search(verification_status="verified")
        self.assertEqual(len(verified_cases), 1)

        synthetic_cases = self.repo.search(is_synthetic=True)
        self.assertEqual(len(synthetic_cases), 1)
        self.assertEqual(synthetic_cases[0].case_id, "CASE-ELEV-002")

    def test_search_full_text(self):
        """Full-text search should match words across symptoms and root cause."""
        self.repo.add([self.case_1, self.case_2])

        results = self.repo.search(query="chopper")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].case_id, "CASE-ELEV-002")

        sill_results = self.repo.search(query="debris")
        self.assertEqual(len(sill_results), 1)
        self.assertEqual(sill_results[0].case_id, "CASE-ELEV-001")

    def test_update_method(self):
        """update() should modify attributes and re-validate."""
        self.repo.add(self.case_1)
        updated = self.repo.update("CASE-ELEV-001", {"fault_code": "E-DR-999"})
        self.assertEqual(updated.fault_code, "E-DR-999")

        retrieved = self.repo.get("CASE-ELEV-001")
        self.assertEqual(retrieved.fault_code, "E-DR-999")

    def test_delete(self):
        """delete() should remove the record from database."""
        self.repo.add(self.case_1)
        self.assertTrue(self.repo.delete("CASE-ELEV-001"))
        self.assertIsNone(self.repo.get("CASE-ELEV-001"))
        self.assertFalse(self.repo.delete("CASE-ELEV-001"))

    def test_export_json(self):
        """export() with json format should create a valid JSON file."""
        self.repo.add([self.case_1, self.case_2])
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "exported_cases.json"
            exported_count = self.repo.export(out_path, format_type="json")
            self.assertEqual(exported_count, 2)
            self.assertTrue(out_path.exists())

            data = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(len(data), 2)

    def test_export_csv(self):
        """export() with csv format should create a valid CSV file."""
        self.repo.add([self.case_1, self.case_2])
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "exported_cases.csv"
            exported_count = self.repo.export(out_path, format_type="csv")
            self.assertEqual(exported_count, 2)
            self.assertTrue(out_path.exists())
            content = out_path.read_text(encoding="utf-8")
            self.assertIn("CASE-ELEV-001", content)
            self.assertIn("CASE-ELEV-002", content)

    def test_indexing_workflow(self):
        """get_unindexed() and mark_as_indexed() should manage vector index state."""
        self.repo.add([self.case_1, self.case_2])

        unindexed = self.repo.get_unindexed()
        self.assertEqual(len(unindexed), 2)

        marked_count = self.repo.mark_as_indexed(["CASE-ELEV-001"])
        self.assertEqual(marked_count, 1)

        unindexed_after = self.repo.get_unindexed()
        self.assertEqual(len(unindexed_after), 1)
        self.assertEqual(unindexed_after[0].case_id, "CASE-ELEV-002")


if __name__ == "__main__":
    unittest.main()
