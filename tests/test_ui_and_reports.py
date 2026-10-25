"""Targeted tests for UI telemetry parsing, DiagnosticEnricher, PDF/JSON report generation, and navigation."""

import io
import json
import unittest

from src.diagnosis.diagnostic_enricher import DiagnosticDossier, DiagnosticEnricher
from src.ui.pages.new_investigation import (
    parse_telemetry_file,
    validate_and_parse_telemetry_upload,
)
from src.utils.report_generator import DiagnosticReportGenerator


class DummyUploadFile:
    """Mock Streamlit uploaded file object."""

    def __init__(self, name: str, data: bytes):
        self.name = name
        self.data = data

    def getvalue(self) -> bytes:
        return self.data


class TestUIAndReportsUpgrade(unittest.TestCase):
    """Validates the redesigned UI helpers, telemetry validators, and report generator."""

    def setUp(self):
        self.sample_inv_data = {
            "investigation_id": "INV-UPGRADE-TEST-001",
            "elevator_id": "ELV-CAR-04",
            "building_id": "Commercial Plaza Tower B",
            "subsystem": "door_system",
            "fault_code": "E-DR-201",
            "symptoms": [
                "Car door reopens repeatedly without passenger obstruction",
                "Door dwell timer expires causing nudging buzzer activation",
            ],
            "telemetry": {
                "curtain_optical_attenuation_db": 6.8,
                "motor_current_peak_a": 3.8,
                "door_open_close_cycles": 142500,
            },
            "root_cause_hypothesis": "Accumulated grit in car bottom sill guide track causing optical curtain transmitter misalignment.",
            "recommended_actions": "1. Vacuum and clean door sill track grooves.\n2. Realign optical curtain brackets.",
            "confidence_score": 0.92,
            "matched_case_ids": ["CASE-SYNTH-ELEV-001"],
            "status": "completed",
            "technician_notes": "Tested in field.",
            "verification_record": {
                "final_status": "verified_and_finalized",
                "final_verdict": "sufficient",
                "total_retries": 0,
                "max_retries": 2,
                "steps": [
                    {
                        "step_number": 1,
                        "action_taken": "initial_evidence_verification",
                        "verdict": "sufficient",
                        "supported_claims": 2,
                        "unsupported_claims": 0,
                        "contradicted_claims": 0,
                        "retrieved_case_ids": ["CASE-SYNTH-ELEV-001"],
                        "reasons": ["All draft claims grounded in OEM bulletin."],
                    }
                ],
            },
            "retry_count": 0,
            "diagnostic_report": {
                "candidate_causes": [
                    {
                        "rank": 1,
                        "hypothesis_title": "Door Sill Grit Obstruction",
                        "subsystem": "door_system",
                        "probability_band": "likely",
                        "explanation": "Debris accumulated in sill groove obstructing optical curtain path.",
                        "supporting_case_ids": ["CASE-SYNTH-ELEV-001"],
                        "recommended_checks": ["Measure optical receiver attenuation", "Inspect sill tracks"],
                        "documented_corrective_actions": ["Clean sill grooves", "Realign transmitter"],
                    }
                ],
                "safety_advisories": [
                    "LOTO: Lock mainline disconnect before adjusting door operator.",
                ],
            },
        }

    # -------------------------------------------------------------------------
    # Telemetry Validation & Parsing Tests
    # -------------------------------------------------------------------------

    def test_upload_valid_json_object(self):
        """Parses a valid single-object JSON telemetry file."""
        raw_json = json.dumps({"motor_current_a": 4.2, "temperature_c": 32.5}).encode("utf-8")
        upload = DummyUploadFile("telemetry.json", raw_json)
        valid, data, err, meta = validate_and_parse_telemetry_upload(upload)
        self.assertTrue(valid)
        self.assertIsNone(err)
        self.assertEqual(data["motor_current_a"], 4.2)
        self.assertEqual(data["temperature_c"], 32.5)

    def test_upload_valid_json_list_of_objects(self):
        """Parses a JSON file containing a list with a dictionary."""
        raw_json = json.dumps([{"bus_voltage_v": 680, "vibration_m_s2": 0.05}]).encode("utf-8")
        upload = DummyUploadFile("readings.json", raw_json)
        valid, data, err, meta = validate_and_parse_telemetry_upload(upload)
        self.assertTrue(valid)
        self.assertEqual(data["bus_voltage_v"], 680)

    def test_upload_malformed_json_returns_actionable_error(self):
        """Rejects malformed JSON with specific error syntax details."""
        raw_json = b"{'invalid_quotes': 123"
        upload = DummyUploadFile("corrupt.json", raw_json)
        valid, data, err, meta = validate_and_parse_telemetry_upload(upload)
        self.assertFalse(valid)
        self.assertIn("Malformed JSON", err)

    def test_upload_empty_file_rejected(self):
        """Rejects empty 0-byte uploaded files."""
        upload = DummyUploadFile("empty.json", b"")
        valid, data, err, meta = validate_and_parse_telemetry_upload(upload)
        self.assertFalse(valid)
        self.assertIn("completely empty", err)

    def test_upload_valid_key_value_csv(self):
        """Parses a 2-column key-value CSV."""
        raw_csv = b"curtain_optical_attenuation_db,6.8\nmotor_current_peak_a,3.8\n"
        upload = DummyUploadFile("sensor.csv", raw_csv)
        valid, data, err, meta = validate_and_parse_telemetry_upload(upload)
        self.assertTrue(valid)
        self.assertEqual(data["curtain_optical_attenuation_db"], 6.8)
        self.assertEqual(data["motor_current_peak_a"], 3.8)

    def test_upload_tabular_csv_with_header(self):
        """Parses tabular multi-column CSV."""
        raw_csv = b"speed_mps,vibration_m_s2,floor_level_error_mm\n1.75,0.08,3.2\n"
        upload = DummyUploadFile("flight.csv", raw_csv)
        valid, data, err, meta = validate_and_parse_telemetry_upload(upload)
        self.assertTrue(valid)
        self.assertEqual(data["speed_mps"], 1.75)
        self.assertEqual(data["floor_level_error_mm"], 3.2)

    def test_upload_invalid_extension_rejected(self):
        """Rejects unsupported file formats (e.g. .txt, .exe, .pdf)."""
        upload = DummyUploadFile("telemetry.txt", b"some text")
        valid, data, err, meta = validate_and_parse_telemetry_upload(upload)
        self.assertFalse(valid)
        self.assertIn("Unsupported file extension", err)

    # -------------------------------------------------------------------------
    # Diagnostic Enricher Tests
    # -------------------------------------------------------------------------

    def test_enrich_investigation_returns_all_18_attributes(self):
        """Enriches raw session into complete 18-point DiagnosticDossier."""
        dossier = DiagnosticEnricher.enrich_investigation(self.sample_inv_data)
        self.assertIsInstance(dossier, DiagnosticDossier)
        self.assertEqual(dossier.investigation_id, "INV-UPGRADE-TEST-001")
        self.assertEqual(dossier.elevator_id, "ELV-CAR-04")
        self.assertEqual(dossier.subsystem, "door_system")
        self.assertEqual(dossier.fault_code, "E-DR-201")
        self.assertTrue(dossier.is_verified)
        self.assertGreater(len(dossier.required_tools), 0)
        self.assertGreater(len(dossier.safety_precautions), 0)
        self.assertGreater(len(dossier.return_to_service_checks), 0)
        self.assertGreater(dossier.downtime_estimate.total_hours, 0)

    def test_enrich_tools_have_required_fields(self):
        """Verifies each tool has Name, Purpose, Why Needed, Inspection Step, Safety."""
        dossier = DiagnosticEnricher.enrich_investigation(self.sample_inv_data)
        for t in dossier.required_tools:
            self.assertTrue(t.name)
            self.assertTrue(t.purpose)
            self.assertTrue(t.why_needed)
            self.assertTrue(t.inspection_step)
            self.assertTrue(t.safety_precautions)

    def test_enrich_parts_grounded_in_evidence(self):
        """Verifies part recommendations are only generated when supported by telemetry or symptoms."""
        dossier = DiagnosticEnricher.enrich_investigation(self.sample_inv_data)
        # Attenuation is 6.8 dB (> 6.0 threshold), so optical sensor bar should be recommended
        part_names = [p.part_name for p in dossier.recommended_parts]
        self.assertTrue(any("Optical" in name for name in part_names))

    def test_troubleshooting_manual_generation_and_step_attributes(self):
        """Verifies step-by-step troubleshooting manual is populated with required fields."""
        dossier = DiagnosticEnricher.enrich_investigation(self.sample_inv_data)
        self.assertGreater(len(dossier.troubleshooting_manual), 0)

        # Check step fields
        for step in dossier.troubleshooting_manual:
            self.assertGreater(step.step_number, 0)
            self.assertTrue(step.title)
            self.assertIn(step.step_type.lower(), ["diagnostic inspection", "corrective action", "verification", "verification check"])
            self.assertTrue(step.purpose)
            self.assertTrue(step.required_tools)
            self.assertTrue(step.inspection_measurement)
            self.assertTrue(step.expected_criterion)
            self.assertTrue(step.interpretation)
            self.assertTrue(step.next_action)
            self.assertTrue(step.safety_precautions)

        # Confirm diagnostic inspection is clearly separated from corrective action
        step_types_lower = [s.step_type.lower() for s in dossier.troubleshooting_manual]
        self.assertIn("diagnostic inspection", step_types_lower)
        self.assertIn("corrective action", step_types_lower)

    def test_evidence_based_status_classification(self):
        """Tests that evidence-based status accurately reflects verification and data sufficiency."""
        # 1. Verified and grounded case with DTC and telemetry -> Evidence Supported
        dossier_verified = DiagnosticEnricher.enrich_investigation(self.sample_inv_data)
        self.assertEqual(dossier_verified.evidence_based_status, "Evidence Supported")

        # 2. Inconclusive verification verdict -> Insufficient Evidence
        unverified_inv = dict(self.sample_inv_data)
        unverified_inv["verification_record"] = {"final_verdict": "insufficient"}
        unverified_inv["status"] = "inconclusive"
        dossier_unverified = DiagnosticEnricher.enrich_investigation(unverified_inv)
        self.assertNotEqual(dossier_unverified.evidence_based_status, "Evidence Supported")
        self.assertIn(dossier_unverified.evidence_based_status, ["Insufficient Evidence", "Partially Supported", "Review Required"])

        # 3. Grounded hypothesis but missing telemetry -> Review Required (technician multimeter check needed)
        limited_inv = dict(self.sample_inv_data)
        limited_inv["telemetry"] = {}
        dossier_limited = DiagnosticEnricher.enrich_investigation(limited_inv)
        self.assertEqual(dossier_limited.evidence_based_status, "Review Required")

        # 4. Sparse symptoms without DTC, telemetry, or evidence -> Insufficient Evidence
        sparse_inv = dict(self.sample_inv_data)
        sparse_inv["fault_code"] = None
        sparse_inv["telemetry"] = {}
        sparse_inv["symptoms"] = ["Door problem"]
        sparse_inv["evidence_package"] = {"items": []}
        sparse_inv["matched_cases"] = []
        sparse_inv["matched_case_ids"] = []
        sparse_inv["verification_record"] = {"final_verdict": "insufficient"}
        sparse_inv["confidence_score"] = 0.15
        dossier_sparse = DiagnosticEnricher.enrich_investigation(sparse_inv)
        self.assertEqual(dossier_sparse.evidence_based_status, "Insufficient Evidence")

    # -------------------------------------------------------------------------
    # PDF and JSON Report Generator Tests
    # -------------------------------------------------------------------------

    def test_generate_pdf_creates_valid_document(self):
        """Generates a non-empty PDF binary containing standard PDF header and multiple pages."""
        pdf_bytes = DiagnosticReportGenerator.generate_pdf(self.sample_inv_data)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 10000)
        # Standard PDF magic header check
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        # Multi-page check
        page_markers = pdf_bytes.count(b"/Type /Page\n") + pdf_bytes.count(b"/Type /Page/")
        self.assertGreaterEqual(page_markers, 2)

    def test_generate_json_export_is_valid(self):
        """Exports a valid, parseable JSON diagnostic dossier."""
        json_str = DiagnosticReportGenerator.generate_json(self.sample_inv_data)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["investigation_id"], "INV-UPGRADE-TEST-001")
        self.assertEqual(parsed["export_schema_version"], "2.0.0")
        self.assertIn("required_tools", parsed)
        self.assertIn("return_to_service_checks", parsed)
        self.assertIn("downtime_estimate", parsed)
        self.assertIn("troubleshooting_manual", parsed)
        self.assertIn("evidence_based_status", parsed)
        self.assertEqual(parsed["evidence_based_status"], "Evidence Supported")

    # -------------------------------------------------------------------------
    # Logo and Branding Rendering Tests
    # -------------------------------------------------------------------------

    def test_logo_data_uri_and_html_generation(self):
        """Verifies logo generates a base64 Data URI image tag without multiline code triggers."""
        from src.ui.assets.logo import get_faultsense_svg, get_logo_data_uri, get_logo_html

        svg = get_faultsense_svg(width=180, height=44, show_text=True)
        self.assertTrue(svg.startswith("<svg"))
        self.assertTrue(svg.endswith("</svg>"))
        # Must be single-line to avoid CommonMark code block indents
        self.assertNotIn("\n", svg)

        data_uri = get_logo_data_uri(width=180, height=44)
        self.assertTrue(data_uri.startswith("data:image/svg+xml;base64,"))

        img_html = get_logo_html(width=48, height=44, show_text=False)
        self.assertTrue(img_html.startswith("<img src=\"data:image/svg+xml;base64,"))
        self.assertIn("width=\"48\"", img_html)
        self.assertIn("height=\"44\"", img_html)
        self.assertNotIn("\n", img_html)

    # -------------------------------------------------------------------------
    # Redesigned Sidebar Subsystem Status & Safety Disclaimer Tests
    # -------------------------------------------------------------------------

    def test_sidebar_status_panel_and_disclaimer(self):
        """Verifies status panel and disclaimer functions execute and generate expected classes."""
        from unittest.mock import MagicMock, patch
        from config.settings import get_settings
        from src.ui.components.sidebar import render_safety_disclaimer, render_subsystem_status

        settings = get_settings()

        with patch("streamlit.markdown") as mock_markdown:
            render_subsystem_status(settings)
            self.assertTrue(mock_markdown.called)
            # Find the call with fs-status-panel
            rendered_panel_html = ""
            for call in mock_markdown.call_args_list:
                arg = call[0][0] if call[0] else ""
                if "fs-status-panel" in arg:
                    rendered_panel_html = arg
                    break

            self.assertTrue(rendered_panel_html, "fs-status-panel HTML was not rendered")
            self.assertIn("System Mode", rendered_panel_html)
            self.assertIn("Database", rendered_panel_html)
            self.assertIn("Vector Store", rendered_panel_html)
            self.assertIn("Embedding Model", rendered_panel_html)
            self.assertIn("fs-pulse-dot", rendered_panel_html)

        with patch("streamlit.markdown") as mock_markdown, patch("streamlit.expander") as mock_expander:
            mock_expander.return_value.__enter__ = MagicMock()
            mock_expander.return_value.__exit__ = MagicMock()

            render_safety_disclaimer()
            self.assertTrue(mock_markdown.called)
            rendered_disc_html = ""
            for call in mock_markdown.call_args_list:
                arg = call[0][0] if call[0] else ""
                if "fs-disclaimer-card" in arg:
                    rendered_disc_html = arg
                    break

    def test_technician_review_persistence_and_signoff_in_pdf(self):
        """Verifies technician review can be persisted and renders into the PDF sign-off block."""
        import uuid
        from src.storage.repository import InvestigationRepository

        repo = InvestigationRepository()
        test_inv_data = dict(self.sample_inv_data)
        test_inv_data["investigation_id"] = f"INV-TEST-REV-{uuid.uuid4().hex[:8]}"
        inv_id = repo.create(test_inv_data)

        # Update with technician review
        review_data = {
            "technician_name": "Marcus Vance, QEI-1",
            "certification_number": "QEI-88329-NY",
            "verification_outcome": "Confirmed AI Root Cause Correct — Fault Resolved",
            "physical_resolution_status": "Physically Resolved & Tested per ASME A17.1",
            "reviewed_at": "2026-10-25T14:30:00Z",
            "chk_loto": True,
            "chk_mech": True,
            "chk_elec": True,
            "chk_align": True,
            "chk_test": True,
            "chk_house": True,
        }
        success = repo.update_technician_review(
            investigation_id=inv_id,
            technician_notes="Door sill cleaned with HEPA vacuum. Optical curtain aligned to 24.0V DC. Full travel verified.",
            review_data=review_data,
            status="completed",
        )
        self.assertTrue(success)

        # Retrieve and verify persistence
        updated_rec = repo.get(inv_id)
        self.assertIsNotNone(updated_rec)
        self.assertIn("technician_review", updated_rec)
        self.assertEqual(updated_rec["technician_review"]["technician_name"], "Marcus Vance, QEI-1")
        self.assertEqual(updated_rec["status"], "completed")

        # Generate PDF with technician sign-off
        pdf_bytes = DiagnosticReportGenerator.generate_pdf(updated_rec)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertGreater(len(pdf_bytes), 10000)

    def test_diagnostic_report_page_import_and_structure(self):
        """Verifies diagnostic_report page can be imported and sidebar includes report item."""
        from src.ui.components.sidebar import NAV_ITEMS
        from src.ui.pages.diagnostic_report import render_diagnostic_report_page

        self.assertTrue(callable(render_diagnostic_report_page))
        nav_ids = [item[0] for item in NAV_ITEMS]
        self.assertIn("report", nav_ids)

    def test_st_text_area_parameters_are_valid(self):
        """Ensures that no UI file passes unsupported arguments like 'rows' to st.text_area."""
        import ast
        import os

        ui_dir = os.path.join(os.path.dirname(__file__), "..", "src", "ui")
        for root, _, files in os.walk(ui_dir):
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    with open(full_path, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read(), filename=full_path)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            # Check for st.text_area or text_area calls
                            is_text_area = False
                            if isinstance(node.func, ast.Attribute) and node.func.attr == "text_area":
                                is_text_area = True
                            elif isinstance(node.func, ast.Name) and node.func.id == "text_area":
                                is_text_area = True

                            if is_text_area:
                                kwarg_names = [kw.arg for kw in node.keywords if kw.arg is not None]
                                self.assertNotIn(
                                    "rows",
                                    kwarg_names,
                                    f"File {file} uses unsupported 'rows' kwarg in st.text_area! Use 'height' instead.",
                                )


if __name__ == "__main__":
    unittest.main()
