"""Unit tests for Pandas and NumPy preprocessing utilities."""

import unittest
import numpy as np
import pandas as pd

from fault_sense.preprocessor import (
    clean_text,
    compute_sensor_statistics,
    dataframe_to_fault_cases,
    normalize_symptoms,
    normalize_telemetry,
    preprocess_fault_dataframe,
    zscore_normalize,
)


class TestPreprocessor(unittest.TestCase):
    """Tests preprocessing and numerical signal transformation functions."""

    def test_clean_text_normalizations(self):
        """clean_text should strip whitespace and collapse consecutive spaces."""
        raw = "   Fault   in  door   drive   \n\t system \x00 "
        cleaned = clean_text(raw)
        self.assertEqual(cleaned, "Fault in door drive system")

    def test_clean_text_none_and_nan(self):
        """clean_text should handle None and NaN gracefully."""
        self.assertEqual(clean_text(None), "")
        self.assertEqual(clean_text(np.nan), "")

    def test_normalize_symptoms_from_various_inputs(self):
        """normalize_symptoms should handle list, comma-separated, and JSON array inputs."""
        # Comma separated
        res1 = normalize_symptoms("Door jitter, motor hum, door jitter")
        self.assertEqual(res1, ["Door jitter", "motor hum"])

        # Semicolon separated
        res2 = normalize_symptoms("Alarm sounded; Car held at floor 3")
        self.assertEqual(res2, ["Alarm sounded", "Car held at floor 3"])

        # JSON array string
        res3 = normalize_symptoms('["Nudging buzzer active", "Door reopened"]')
        self.assertEqual(res3, ["Nudging buzzer active", "Door reopened"])

        # Empty / None
        self.assertEqual(normalize_symptoms(None), [])
        self.assertEqual(normalize_symptoms(""), [])

    def test_normalize_telemetry_numeric_parsing(self):
        """normalize_telemetry should cast strings to ints/floats and handle NaN."""
        raw = {
            "motor_temp": "65.4",
            "vibration_g": 0.35,
            "cycle_count": "15000",
            "active": "true",
            "invalid_sensor": np.nan,
        }
        res = normalize_telemetry(raw)
        self.assertEqual(res["motor_temp"], 65.4)
        self.assertEqual(res["vibration_g"], 0.35)
        self.assertEqual(res["cycle_count"], 15000)
        self.assertTrue(res["active"])
        self.assertIsNone(res["invalid_sensor"])

    def test_normalize_telemetry_from_json_string(self):
        """normalize_telemetry should parse JSON strings."""
        raw_json = '{"dc_bus_v": "720.5", "braking_chopper_on": true}'
        res = normalize_telemetry(raw_json)
        self.assertEqual(res["dc_bus_v"], 720.5)
        self.assertTrue(res["braking_chopper_on"])

    def test_compute_sensor_statistics_numpy(self):
        """compute_sensor_statistics should compute mean, std, percentiles and RMS accurately."""
        readings = [10.0, 20.0, 30.0, 40.0, 50.0]
        stats = compute_sensor_statistics(readings)

        self.assertEqual(stats["count"], 5)
        self.assertEqual(stats["mean"], 30.0)
        self.assertEqual(stats["min"], 10.0)
        self.assertEqual(stats["max"], 50.0)
        self.assertEqual(stats["p50"], 30.0)
        self.assertGreater(stats["rms"], 0)

        # Test empty series handling
        empty_stats = compute_sensor_statistics([])
        self.assertEqual(empty_stats["count"], 0)
        self.assertEqual(empty_stats["mean"], 0.0)

    def test_zscore_normalize(self):
        """zscore_normalize should compute standardized score."""
        val = 70.0
        mean = 50.0
        std = 10.0
        z = zscore_normalize(val, mean, std)
        self.assertEqual(z, 2.0)

    def test_preprocess_fault_dataframe(self):
        """preprocess_fault_dataframe should standardize columns and coerce types."""
        raw_df = pd.DataFrame([
            {
                "Case_ID": "CASE-DF-01",
                "Source_Title": "Test Title",
                "Source_Reference": "REF-01",
                "Source_Type": "synthetic_illustrative",
                "Verification_Status": "unverified",
                "Subsystem": "door_system",
                "Fault_Code": "E-01",
                "Symptoms": "Door slow; sill dirty",
                "Telemetry_Summary": '{"speed": "0.4"}',
                "Confirmed_Root_Cause": "Dirt",
                "Corrective_Action": "Cleaned",
            }
        ])

        clean_df, issues = preprocess_fault_dataframe(raw_df)
        self.assertIn("case_id", clean_df.columns)
        self.assertIn("symptoms", clean_df.columns)
        self.assertIsInstance(clean_df.iloc[0]["symptoms"], list)
        self.assertIsInstance(clean_df.iloc[0]["telemetry_summary"], dict)

    def test_dataframe_to_fault_cases(self):
        """dataframe_to_fault_cases should convert valid rows and flag invalid rows."""
        df = pd.DataFrame([
            {
                "case_id": "CASE-OK-01",
                "source_title": "OK Title",
                "source_reference": "REF-OK",
                "source_type": "synthetic_illustrative",
                "verification_status": "unverified",
                "subsystem": "door_system",
                "fault_code": "E-01",
                "symptoms": ["Door stuck"],
                "telemetry_summary": {"cycles": 10},
                "confirmed_root_cause": "Friction",
                "corrective_action": "Oiled",
            },
            {
                "case_id": "CASE-ERR-02",
                "source_title": "",  # Invalid: empty title
                "source_reference": "REF-ERR",
                "source_type": "synthetic_illustrative",
                "verification_status": "unverified",
                "subsystem": "door_system",
                "fault_code": "E-02",
                "symptoms": ["Door stuck"],
                "telemetry_summary": {},
                "confirmed_root_cause": "Friction",
                "corrective_action": "Oiled",
            },
        ])

        valid_cases, errors = dataframe_to_fault_cases(df)
        self.assertEqual(len(valid_cases), 1)
        self.assertEqual(valid_cases[0].case_id, "CASE-OK-01")
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["case_id"], "CASE-ERR-02")


if __name__ == "__main__":
    unittest.main()
