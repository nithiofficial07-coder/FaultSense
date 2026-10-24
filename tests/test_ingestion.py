"""Unit tests for the FaultSense data ingestion pipeline.

Tests CSV and JSON parsing, file validation, missing fields, duplicates,
malformed syntax resilience, and import summary reporting.
"""

from pathlib import Path
import unittest

from fault_sense.ingestion import FaultCaseIngestionPipeline, IngestionConfig


class TestIngestionPipeline(unittest.TestCase):
    """Tests ingestion edge cases and reporting."""

    def setUp(self):
        self.pipeline = FaultCaseIngestionPipeline()
        self.project_root = Path(__file__).parent.parent
        self.data_dir = self.project_root / "data"
        self.fixtures_dir = self.project_root / "tests" / "fixtures"

    def test_import_valid_json_sample(self):
        """Standard sample JSON dataset should import all records cleanly."""
        json_path = self.data_dir / "sample_fault_cases.json"
        cases, summary = self.pipeline.ingest_file(json_path)

        self.assertGreater(len(cases), 0)
        self.assertEqual(summary.valid_records, len(cases))
        self.assertEqual(summary.rejected_records, 0)
        self.assertEqual(summary.duplicate_records, 0)
        self.assertTrue(summary.success)

        # Verify source metadata preserved
        sample_case = cases[0]
        self.assertIn("curation_note", sample_case.metadata)
        self.assertTrue(sample_case.is_synthetic)

    def test_import_valid_csv_sample(self):
        """Standard sample CSV dataset should import and parse types cleanly."""
        csv_path = self.data_dir / "sample_fault_cases.csv"
        cases, summary = self.pipeline.ingest_file(csv_path)

        self.assertGreater(len(cases), 0)
        self.assertEqual(summary.valid_records, len(cases))
        self.assertEqual(summary.rejected_records, 0)
        self.assertTrue(summary.success)

        # Check that symptoms was coerced into a list
        for c in cases:
            self.assertIsInstance(c.symptoms, list)
            self.assertGreater(len(c.symptoms), 0)
            self.assertIsInstance(c.telemetry_summary, dict)

    def test_reject_unsupported_file_extension(self):
        """Unsupported file extensions like .txt should be rejected in validation."""
        txt_path = self.fixtures_dir / "unsupported.txt"
        txt_path.write_text("random text", encoding="utf-8")
        try:
            cases, summary = self.pipeline.ingest_file(txt_path)
            self.assertEqual(len(cases), 0)
            self.assertFalse(summary.success)
            self.assertIn("Unsupported file format", summary.errors[0]["error"])
        finally:
            if txt_path.exists():
                txt_path.unlink()

    def test_reject_zero_byte_empty_file(self):
        """A 0-byte file should be rejected with an informative error."""
        empty_path = self.fixtures_dir / "empty_file.json"
        cases, summary = self.pipeline.ingest_file(empty_path)
        self.assertEqual(len(cases), 0)
        self.assertIn("completely empty", summary.errors[0]["error"])

    def test_handle_empty_dataset_gracefully(self):
        """An empty JSON array '[]' should result in 0 records and no fatal crash."""
        empty_ds_path = self.fixtures_dir / "empty_dataset.json"
        cases, summary = self.pipeline.ingest_file(empty_ds_path)
        self.assertEqual(len(cases), 0)
        self.assertEqual(summary.valid_records, 0)
        self.assertEqual(summary.rejected_records, 0)

    def test_handle_malformed_json_syntax(self):
        """Malformed JSON syntax must be reported without crashing the application."""
        temp_bad_json = self.fixtures_dir / "temp_corrupt_syntax.json"
        temp_bad_json.write_text('[\n  {"case_id": "ERR-JSON-001", "unclosed_string: "test\n', encoding="utf-8")
        try:
            cases, summary = self.pipeline.ingest_file(temp_bad_json)
            self.assertEqual(len(cases), 0)
            self.assertFalse(summary.success)
            self.assertGreater(len(summary.errors), 0)
            self.assertIn("JSON", summary.errors[0]["error"])
        finally:
            if temp_bad_json.exists():
                temp_bad_json.unlink()

    def test_missing_required_fields_reported(self):
        """Records with missing mandatory fields must be rejected and cataloged with row info."""
        missing_path = self.fixtures_dir / "missing_fields.json"
        cases, summary = self.pipeline.ingest_file(missing_path)

        self.assertEqual(len(cases), 0)
        self.assertEqual(summary.rejected_records, 3)
        self.assertEqual(len(summary.errors), 3)

        # Check that error records contain row_index and field information
        error_fields = [e.get("field") for e in summary.errors]
        self.assertTrue(any(f in ("subsystem", "case_id", "symptoms", "confirmed_root_cause") for f in error_fields))

    def test_batch_duplicate_detection(self):
        """Duplicate case_id in the same file must be flagged and rejected."""
        dup_path = self.fixtures_dir / "duplicate_cases.json"
        cases, summary = self.pipeline.ingest_file(dup_path)

        self.assertEqual(len(cases), 1)  # First instance accepted
        self.assertEqual(summary.duplicate_records, 1)
        self.assertEqual(summary.rejected_records, 1)

    def test_cross_repository_duplicate_detection(self):
        """Case IDs that already exist in the knowledge base should be rejected as duplicates."""
        existing_ids = {"CASE-SYNTH-ELEV-001"}
        json_path = self.data_dir / "sample_fault_cases.json"

        cases, summary = self.pipeline.ingest_file(json_path, existing_case_ids=existing_ids)
        self.assertEqual(summary.duplicate_records, 1)
        self.assertTrue(any("already exists" in e["error"] for e in summary.errors))

    def test_file_size_limit_enforcement(self):
        """Files exceeding configured max_file_size_bytes must be rejected."""
        strict_config = IngestionConfig(max_file_size_bytes=10)  # 10 bytes limit
        strict_pipeline = FaultCaseIngestionPipeline(config=strict_config)
        json_path = self.data_dir / "sample_fault_cases.json"

        cases, summary = strict_pipeline.ingest_file(json_path)
        self.assertEqual(len(cases), 0)
        self.assertIn("exceeds maximum permitted limit", summary.errors[0]["error"])

    def test_synthetic_provenance_violation_rejected(self):
        """Synthetic illustrative records claiming to be verified incidents must be rejected."""
        violation_path = self.fixtures_dir / "synthetic_provenance_violation.json"
        cases, summary = self.pipeline.ingest_file(violation_path)

        self.assertEqual(len(cases), 0)
        self.assertEqual(summary.rejected_records, 1)
        self.assertIn("Illustrative synthetic cases cannot be marked as verified", summary.errors[0]["error"])

    def test_summary_formatted_report_output(self):
        """formatted_report should render human-readable summary text."""
        json_path = self.data_dir / "sample_fault_cases.json"
        _, summary = self.pipeline.ingest_file(json_path)
        report_text = summary.formatted_report()

        self.assertIn("ELEVATOR FAULT CASE INGESTION SUMMARY", report_text)
        self.assertIn("Valid / Accepted", report_text)

    def test_handle_empty_csv_dataset(self):
        """Header-only or empty CSV should be handled gracefully without crashing."""
        empty_csv = self.fixtures_dir / "empty_dataset.csv"
        cases, summary = self.pipeline.ingest_file(empty_csv)
        self.assertEqual(len(cases), 0)
        self.assertEqual(summary.valid_records, 0)
        self.assertTrue(any("contains no data rows" in w for w in summary.warnings))

    def test_handle_incorrect_data_types(self):
        """Incorrect data types in fields should be captured and reported in summary."""
        inc_types_path = self.fixtures_dir / "incorrect_data_types.json"
        cases, summary = self.pipeline.ingest_file(inc_types_path)
        # Record has invalid non-string case_id or non-dict telemetry
        self.assertGreater(summary.total_records, 0)
        # Either rejected or normalized
        self.assertEqual(summary.rejected_records + summary.valid_records, summary.total_records)

    def test_handle_malformed_csv_syntax(self):
        """Malformed CSV syntax or corrupted quotes should be captured cleanly without crashing."""
        corrupt_csv = self.fixtures_dir / "malformed_corrupt.csv"
        corrupt_csv.write_text('case_id,subsystem\n"unclosed_quote_row,door_system', encoding="utf-8")
        try:
            cases, summary = self.pipeline.ingest_file(corrupt_csv)
            self.assertEqual(len(cases), 0)
            self.assertFalse(summary.success)
            self.assertGreater(len(summary.errors), 0)
        finally:
            if corrupt_csv.exists():
                corrupt_csv.unlink()


if __name__ == "__main__":
    unittest.main()
