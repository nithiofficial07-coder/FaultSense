"""New Investigation workflow page for elevator technician decision support.

Features structured incident intake, reliable CSV/JSON upload validation,
interactive JSON telemetry editor with live preview, and connection to the
FaultSense agentic diagnostic pipeline.
"""

from __future__ import annotations

import csv
import io
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import streamlit as st

from fault_sense.schema import SubsystemType
from src.diagnosis.diagnostic_enricher import DiagnosticEnricher
from src.diagnosis.engine import DiagnosisEngine
from src.diagnosis.session import DiagnosisRequest
from src.knowledge_base.manager import KnowledgeBaseManager
from src.storage.repository import InvestigationRepository
from src.ui.components.sidebar import navigate_to
from src.utils.logger import get_logger
from src.utils.report_generator import DiagnosticReportGenerator

logger = get_logger(__name__)

# Max upload limit (10 MB is appropriate for sensor telemetry)
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024

DEFAULT_JSON_EXAMPLE = """{
  "door_open_close_cycles": 142500,
  "curtain_optical_attenuation_db": 6.8,
  "motor_current_peak_a": 3.8
}"""

SYMPTOM_PRESETS = {
    "Door System — Reopening": (
        "door_system",
        "E-DR-201",
        "Car door reopens repeatedly without passenger obstruction\nDoor dwell timer buzzer sounding\nIntermittent reopening at intermediate floors",
        "Initial visual check performed on landing sills. Optical curtain alignment tested.",
        "Elevator car doors cycling open and closed repeatedly at Floor 4 without passenger obstruction, preventing departure.",
        '{\n  "door_open_close_cycles": 142500,\n  "curtain_optical_attenuation_db": 6.8,\n  "motor_current_peak_a": 3.8\n}',
    ),
    "Traction Drive — Overvoltage": (
        "traction_drive",
        "E-VFD-404",
        "Drive trips on regenerative overvoltage during downward deceleration under heavy load\nMotor hunting sensation during braking",
        "Machine room ambient temperature 34°C. Dynamic braking resistor cage warm to touch.",
        "VVVF drive controller trips on regenerative overvoltage fault during full-load downward express travel.",
        '{\n  "dc_bus_voltage_v": 785.0,\n  "ambient_temperature_c": 36.2,\n  "motor_rpm": 1420\n}',
    ),
    "Braking System — Air-Gap Drag": (
        "braking_system",
        "E-BRK-102",
        "Burning friction smell reported in machine room after express runs\nBrake shoe fails to lift cleanly on run command",
        "Brake arm visual check reveals friction material residue around brake drum.",
        "Machine room friction smoke odor detected following express descent; brake shoes failing to fully clear drum.",
        '{\n  "brake_coil_current_a": 1.4,\n  "brake_lining_temp_c": 88.5,\n  "lift_switch_delay_ms": 380\n}',
    ),
    "Hoistway Signaling — Pulse Drop": (
        "hoistway_signaling",
        "E-POS-305",
        "Car exhibits sudden jerky leveling oscillation at floor arrivals\nPositioning discrepancy detected between primary tape and motor encoder",
        "Encoder cable shielded harness grounded at controller chassis.",
        "Elevator leveling exhibits jerky hunting motion at terminal landings due to optical encoder pulse count drift.",
        '{\n  "encoder_pulse_deviation": 42,\n  "landing_level_error_mm": 18.5,\n  "guide_rail_vibration_g": 0.08\n}',
    ),
    "Hydraulic System — Valve Contamination": (
        "hydraulic_system",
        "E-HYD-501",
        "Car exhibits downward crawl creep when parked at top terminal landing\nOil temperature alarm logged in controller",
        "Hydraulic fluid last replaced 3 years ago; filter restriction indicator in amber zone.",
        "Hydraulic passenger elevator car slowly sinking below floor landing level when parked under load.",
        '{\n  "hydraulic_oil_temp_c": 64.2,\n  "pump_pressure_psi": 2250,\n  "valve_solenoid_voltage_v": 23.8\n}',
    ),
}


def parse_telemetry_file(uploaded_file: Any) -> Dict[str, Any]:
    """Backward-compatible telemetry file parser used by test suite and UI."""
    is_valid, data, _, _ = validate_and_parse_telemetry_upload(uploaded_file)
    return data if is_valid else {}


def validate_and_parse_telemetry_upload(
    uploaded_file: Any,
) -> Tuple[bool, Dict[str, Any], Optional[str], Dict[str, Any]]:
    """Strictly validates and parses uploaded CSV or JSON telemetry files."""
    if uploaded_file is None:
        return False, {}, "No file provided.", {}

    filename = getattr(uploaded_file, "name", "upload.dat").lower()

    # Get file content safely
    try:
        if hasattr(uploaded_file, "getvalue"):
            content = uploaded_file.getvalue()
        elif hasattr(uploaded_file, "read"):
            content = uploaded_file.read()
        else:
            return False, {}, "Unsupported file object format.", {}
    except Exception as exc:
        return False, {}, f"Unable to read file content: {exc}", {}

    size_bytes = len(content)
    if size_bytes == 0:
        return False, {}, "File is completely empty (0 bytes).", {}

    if size_bytes > MAX_UPLOAD_SIZE_BYTES:
        return (
            False,
            {},
            f"File size ({size_bytes / (1024*1024):.1f} MB) exceeds maximum allowed limit (10 MB).",
            {},
        )

    # Decode UTF-8 safely
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception as exc:
            return False, {}, f"File encoding error. Please ensure file is UTF-8 encoded: {exc}", {}

    meta = {
        "filename": getattr(uploaded_file, "name", "upload"),
        "size_bytes": size_bytes,
        "format": "JSON" if filename.endswith(".json") else ("CSV" if filename.endswith(".csv") else "Unknown"),
    }

    # 1. JSON Parsing
    if filename.endswith(".json"):
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            return False, {}, f"Malformed JSON: {exc.msg} (line {exc.lineno}, column {exc.colno})", meta

        if isinstance(raw, list):
            if not raw:
                return False, {}, "JSON list is empty.", meta
            if not isinstance(raw[0], dict):
                return False, {}, "JSON array items must be key-value dictionaries of telemetry readings.", meta
            raw = raw[0]

        if not isinstance(raw, dict):
            return False, {}, "Root JSON structure must be a dictionary of sensor key-value pairs.", meta

        if not raw:
            return False, {}, "JSON object contains no telemetry keys.", meta

        # Validate numeric conversions
        validated: Dict[str, Any] = {}
        invalid_fields = []
        for k, v in raw.items():
            k_clean = str(k).strip()
            if not k_clean:
                continue
            if isinstance(v, (int, float)):
                validated[k_clean] = v
            else:
                try:
                    num_val = float(str(v).strip())
                    validated[k_clean] = int(num_val) if num_val.is_integer() else num_val
                except (ValueError, TypeError):
                    invalid_fields.append(f"'{k_clean}': '{v}' (expected number)")

        if invalid_fields and len(invalid_fields) == len(raw):
            return False, {}, f"No numeric sensor values could be parsed. Invalid entries: {', '.join(invalid_fields[:3])}", meta

        meta["parsed_count"] = len(validated)
        meta["invalid_fields"] = invalid_fields
        return True, validated, None, meta

    # 2. CSV Parsing
    elif filename.endswith(".csv"):
        try:
            reader = csv.reader(io.StringIO(text))
            rows = [r for r in reader if r and any(cell.strip() for cell in r)]
            if not rows:
                return False, {}, "CSV file contains no readable data rows.", meta

            def try_num(val_str: str) -> Optional[float]:
                try:
                    return float(val_str.strip())
                except (ValueError, TypeError):
                    return None

            # Case A: Two-column key-value format (e.g. parameter,value)
            is_kv_direct = len(rows[0]) == 2 and try_num(rows[0][1]) is not None
            is_kv_header = len(rows[0]) == 2 and rows[0][0].lower().strip() in (
                "parameter", "metric", "sensor", "name", "key", "signal"
            )

            validated = {}
            if is_kv_direct or is_kv_header:
                start_row = 1 if is_kv_header else 0
                for r in rows[start_row:]:
                    if len(r) >= 2 and r[0].strip():
                        val_num = try_num(r[1])
                        if val_num is not None:
                            validated[r[0].strip()] = int(val_num) if val_num.is_integer() else val_num
                        else:
                            validated[r[0].strip()] = r[1].strip()
            else:
                # Case B: Tabular format (row 0 = headers, row 1+ = readings)
                headers = [h.strip() for h in rows[0]]
                if len(rows) > 1:
                    vals = [v.strip() for v in rows[1]]
                    for h, v in zip(headers, vals):
                        if not h:
                            continue
                        val_num = try_num(v)
                        if val_num is not None:
                            validated[h] = int(val_num) if val_num.is_integer() else val_num
                        else:
                            validated[h] = v
                else:
                    return False, {}, "CSV file has headers but contains no data rows.", meta

            if not validated:
                return False, {}, "No valid telemetry fields could be extracted from CSV.", meta

            meta["parsed_count"] = len(validated)
            return True, validated, None, meta

        except Exception as exc:
            return False, {}, f"CSV parsing error: {exc}", meta

    return False, {}, f"Unsupported file extension for '{filename}'. Supported: .csv, .json", meta


KNOWN_FAULT_CODES: List[Tuple[str, str, str]] = [
    ("-- Select known code (or type above) --", "", ""),
    ("E-DR-201 — Door Reopening (Door System)", "E-DR-201", "door_system"),
    ("E-VFD-404 — VVVF Bus Overvoltage (Traction Drive)", "E-VFD-404", "traction_drive"),
    ("E-BRK-302 — Brake Switch Contact Discrepancy (Braking System)", "E-BRK-302", "braking_system"),
    ("E-BRK-102 — Brake Air-Gap Drag (Braking System)", "E-BRK-102", "braking_system"),
    ("E-POS-305 — Hoistway Signaling Pulse Drop (Hoistway Signaling)", "E-POS-305", "hoistway_signaling"),
    ("E-HYD-108 — Hydraulic Releveling Creep (Hydraulic System)", "E-HYD-108", "hydraulic_system"),
    ("E-HYD-501 — Hydraulic Valve Contamination (Hydraulic System)", "E-HYD-501", "hydraulic_system"),
    ("E-CAN-512 — CAN Bus Node Timeout (Controller Electronics)", "E-CAN-512", "controller_electronics"),
    ("FLT-LCK-12 — Landing Lock Interlock Binding (Door System)", "FLT-LCK-12", "door_system"),
]

PRESET_DISPLAY_NAMES = {
    "Door System — Reopening": "Door System — Reopening (E-DR-201: Optical curtain obstruction)",
    "Traction Drive — Overvoltage": "Traction Drive — Overvoltage (E-VFD-404: Regenerative deceleration overvoltage)",
    "Braking System — Air-Gap Drag": "Braking System — Air-Gap Drag (E-BRK-102: Brake shoe friction drag and overheating)",
    "Hoistway Signaling — Pulse Drop": "Hoistway Signaling — Pulse Drop (E-POS-305: Optical encoder pulse drift during leveling)",
    "Hydraulic System — Valve Contamination": "Hydraulic System — Valve Contamination (E-HYD-501: Valve bypass leak causing car creep)",
}


def render_new_investigation_page() -> None:
    """Renders the simplified technician diagnosis intake workflow."""
    # Explanatory subtitle guidance matching reference design
    st.markdown(
        "<div style='color: #64748B; font-size: 0.92rem; line-height: 1.5; margin-bottom: 14px;'>"
        "Enter the fault code shown by the elevator and describe what is happening. FaultSense will evaluate "
        "available records to identify the likely cause and recommended inspection steps."
        "</div>",
        unsafe_allow_html=True,
    )

    # Initialize investigation state containers
    if "telemetry_input_mode" not in st.session_state:
        st.session_state["telemetry_input_mode"] = "file"
    if "uploaded_telemetry_data" not in st.session_state:
        st.session_state["uploaded_telemetry_data"] = {}
    if "manual_json_text" not in st.session_state:
        st.session_state["manual_json_text"] = DEFAULT_JSON_EXAMPLE
    if "auto_incident_id" not in st.session_state:
        st.session_state["auto_incident_id"] = f"INV-{int(time.time()):010d}-{int(time.time() * 1000) % 10000:04d}"

    # Form state default values
    if "widget_fault_code" not in st.session_state:
        st.session_state["widget_fault_code"] = st.session_state.get("fault_code_input", "E-DR-201")
    if "widget_known_code_idx" not in st.session_state:
        cur_code = st.session_state.get("widget_fault_code", "E-DR-201").strip().upper()
        found_idx = 0
        for idx, (label, c, sub) in enumerate(KNOWN_FAULT_CODES):
            if c and c.upper() == cur_code:
                found_idx = idx
                break
        st.session_state["widget_known_code_idx"] = found_idx

    if "widget_symptoms" not in st.session_state:
        st.session_state["widget_symptoms"] = st.session_state.get(
            "symptoms_input",
            "Car door reopens repeatedly without passenger obstruction\nDoor dwell timer buzzer sounding",
        )

    if "widget_elv_id" not in st.session_state:
        st.session_state["widget_elv_id"] = st.session_state.get("saved_elv_id", "ELV-CAR-04")
    if "widget_mfg" not in st.session_state:
        st.session_state["widget_mfg"] = st.session_state.get("saved_mfg", "Otis Elevator Company")
    if "widget_model" not in st.session_state:
        st.session_state["widget_model"] = st.session_state.get("saved_model", "Geared Traction VVVF Passenger (Gen2)")
    if "widget_bldg" not in st.session_state:
        st.session_state["widget_bldg"] = st.session_state.get("saved_bldg_id", "Commercial Plaza Tower B")
    if "widget_sev" not in st.session_state:
        st.session_state["widget_sev"] = st.session_state.get("saved_severity", "High — Service Interruption / Out of Service")
    if "widget_subsystem" not in st.session_state:
        st.session_state["widget_subsystem"] = st.session_state.get("subsystem_picker", "door_system")
    if "widget_op_cond" not in st.session_state:
        st.session_state["widget_op_cond"] = st.session_state.get("saved_op_cond", "Morning peak dispatch; high ambient machine room humidity (82%), 31°C")
    if "widget_extra_codes" not in st.session_state:
        st.session_state["widget_extra_codes"] = st.session_state.get("saved_extra_codes", "")
    if "widget_tech_notes" not in st.session_state:
        st.session_state["widget_tech_notes"] = st.session_state.get("saved_tech_notes", "Initial visual check performed on landing sills. Optical curtain alignment tested.")
    if "widget_addl_narrative" not in st.session_state:
        st.session_state["widget_addl_narrative"] = st.session_state.get("saved_addl_narrative", "")

    # =========================================================================
    # Example Fault Scenarios Expander (Collapsed by default)
    # =========================================================================
    with st.expander("Example fault scenarios (click to test a preset)", expanded=False):
        c_scen, c_load, c_reset = st.columns([2.6, 1.2, 1.2])
        with c_scen:
            selected_preset_key = st.selectbox(
                "Select Failure Scenario Benchmark",
                options=list(SYMPTOM_PRESETS.keys()),
                format_func=lambda k: PRESET_DISPLAY_NAMES.get(k, k),
                key="preset_scenario_selector",
            )
        with c_load:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("Apply Scenario Preset", icon=":material/check:", use_container_width=True, key="btn_apply_preset"):
                preset_data = SYMPTOM_PRESETS[selected_preset_key]
                sub = preset_data[0]
                code = preset_data[1]
                syms = preset_data[2]
                notes = preset_data[3]
                desc = preset_data[4] if len(preset_data) > 4 else syms.splitlines()[0]
                telem_json = preset_data[5] if len(preset_data) > 5 else "{}"

                st.session_state["widget_fault_code"] = code
                st.session_state["fault_code_input"] = code
                st.session_state["fault_code_field"] = code

                matched_idx = 0
                for idx, (label, c, s_sub) in enumerate(KNOWN_FAULT_CODES):
                    if c and c.upper() == code.upper():
                        matched_idx = idx
                        break
                st.session_state["widget_known_code_idx"] = matched_idx

                st.session_state["widget_symptoms"] = syms
                st.session_state["symptoms_input"] = syms
                st.session_state["symptoms_field"] = syms

                st.session_state["widget_subsystem"] = sub
                st.session_state["subsystem_picker"] = sub
                st.session_state["subsystem_select"] = sub

                st.session_state["widget_tech_notes"] = notes
                st.session_state["saved_tech_notes"] = notes
                st.session_state["notes_field"] = notes
                st.session_state["notes_input"] = notes

                st.session_state["widget_addl_narrative"] = desc
                st.session_state["saved_addl_narrative"] = desc
                st.session_state["problem_desc_field"] = desc

                st.session_state["manual_json_text"] = telem_json
                try:
                    st.session_state["uploaded_telemetry_data"] = json.loads(telem_json)
                except Exception:
                    pass
                st.rerun()

        with c_reset:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("Reset Form Fields", icon=":material/refresh:", use_container_width=True, key="btn_reset_form"):
                st.session_state["widget_fault_code"] = ""
                st.session_state["fault_code_input"] = ""
                st.session_state["fault_code_field"] = ""
                st.session_state["widget_known_code_idx"] = 0

                st.session_state["widget_symptoms"] = ""
                st.session_state["symptoms_input"] = ""
                st.session_state["symptoms_field"] = ""

                st.session_state["widget_subsystem"] = "door_system"
                st.session_state["subsystem_picker"] = "door_system"
                st.session_state["subsystem_select"] = "door_system"

                st.session_state["widget_tech_notes"] = ""
                st.session_state["saved_tech_notes"] = ""
                st.session_state["notes_field"] = ""
                st.session_state["notes_input"] = ""

                st.session_state["widget_addl_narrative"] = ""
                st.session_state["saved_addl_narrative"] = ""
                st.session_state["problem_desc_field"] = ""

                st.session_state["widget_extra_codes"] = ""
                st.session_state["saved_extra_codes"] = ""

                st.session_state["manual_json_text"] = "{}"
                st.session_state["uploaded_telemetry_data"] = {}
                st.session_state["current_result"] = None
                st.rerun()

    # =========================================================================
    # Section 1: FAULT INFORMATION (REQUIRED)
    # =========================================================================
    st.markdown(
        f"""
        <div style="background-color: #FFFFFF; border: 1px solid #DCE5F1; border-radius: 8px; padding: 12px 18px; margin-top: 14px; margin-bottom: 14px;">
            <span style="color: #2D58A6; font-size: 0.82rem; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase;">
                1. FAULT INFORMATION (REQUIRED)
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Callbacks for seamless two-way synchronization between text input and dropdown
    def _on_fault_code_text_change() -> None:
        val = st.session_state.get("widget_fault_code", "").strip()
        st.session_state["fault_code_input"] = val
        st.session_state["fault_code_field"] = val
        matched = 0
        for idx, (label, c, sub) in enumerate(KNOWN_FAULT_CODES):
            if c and c.upper() == val.upper():
                matched = idx
                if sub:
                    st.session_state["widget_subsystem"] = sub
                    st.session_state["subsystem_picker"] = sub
                    st.session_state["subsystem_select"] = sub
                break
        st.session_state["widget_known_code_idx"] = matched

    def _on_known_code_dropdown_change() -> None:
        idx = st.session_state.get("widget_known_code_idx", 0)
        if 0 < idx < len(KNOWN_FAULT_CODES):
            c = KNOWN_FAULT_CODES[idx][1]
            sub = KNOWN_FAULT_CODES[idx][2]
            st.session_state["widget_fault_code"] = c
            st.session_state["fault_code_input"] = c
            st.session_state["fault_code_field"] = c
            if sub:
                st.session_state["widget_subsystem"] = sub
                st.session_state["subsystem_picker"] = sub
                st.session_state["subsystem_select"] = sub

    col_code, col_select = st.columns([1, 1])
    with col_code:
        st.text_input(
            "Fault code *",
            placeholder="Enter the fault code shown by the elevator",
            help="Enter the trouble code shown by the elevator controller (e.g. E-DR-201, E-VFD-404) or select from known codes.",
            key="widget_fault_code",
            on_change=_on_fault_code_text_change,
        )

    with col_select:
        st.selectbox(
            "Select known code (or type above)",
            options=range(len(KNOWN_FAULT_CODES)),
            format_func=lambda i: KNOWN_FAULT_CODES[i][0],
            help="Choose a known diagnostic code from the knowledge base or enter manually on the left.",
            key="widget_known_code_idx",
            on_change=_on_known_code_dropdown_change,
        )

    st.text_area(
        "What is happening? *",
        placeholder="Describe the problem in a few words",
        height=110,
        help="Describe observed operational symptoms or passenger reports in plain words.",
        key="widget_symptoms",
    )

    # =========================================================================
    # Additional Details (Optional) Expander
    # =========================================================================
    with st.expander("Additional details (optional)", expanded=False):
        # ---------------------------------------------------------------------
        # Group A: Equipment details
        # ---------------------------------------------------------------------
        st.markdown(
            "<div style='font-size: 0.88rem; font-weight: 700; color: #243247; margin-top: 4px; margin-bottom: 8px; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px;'>"
            "Equipment details"
            "</div>",
            unsafe_allow_html=True,
        )

        eq_col1, eq_col2, eq_col3 = st.columns(3)
        with eq_col1:
            st.text_input(
                "Elevator Unit Identifier",
                placeholder="e.g. ELV-CAR-04, UNIT-B (optional)",
                help="Unique equipment ID assigned by building management or OEM.",
                key="widget_elv_id",
            )
            st.text_input(
                "Building / Job Site Reference",
                placeholder="e.g. Commercial Plaza Tower B",
                help="Facility name, campus, or physical site location.",
                key="widget_bldg",
            )

        with eq_col2:
            mfg_options = [
                "Otis Elevator Company",
                "Schindler Group",
                "KONE Corporation",
                "TK Elevator (Thyssenkrupp)",
                "Mitsubishi Electric",
                "Fujitec",
                "Generic / Other Manufacturer",
            ]
            st.selectbox(
                "Elevator Manufacturer (if known)",
                options=mfg_options,
                help="OEM manufacturer specification helps contextualize schematics and code limits.",
                key="widget_mfg",
            )
            sev_options = [
                "High — Service Interruption / Out of Service",
                "Critical — Safety Circuit Trip / Passenger Entrapment",
                "Medium — Intermittent Fault / Degraded Ride",
                "Low — Routine Preventive Maintenance Finding",
            ]
            st.selectbox(
                "Incident Severity & Urgency Assessment",
                options=sev_options,
                key="widget_sev",
            )

        with eq_col3:
            st.text_input(
                "Elevator Model / Drive Type (if known)",
                placeholder="e.g. 3300 MRL, MonoSpace, TAC32",
                help="Controller family or drive architecture.",
                key="widget_model",
            )
            subsystem_options = [s.value for s in SubsystemType]
            st.selectbox(
                "Affected Subsystem *",
                options=subsystem_options,
                format_func=lambda x: x.replace("_", " ").title(),
                help="Primary physical subsystem exhibiting anomalous behavior.",
                key="widget_subsystem",
            )

        st.text_input(
            "Operating & Environmental Conditions (Optional)",
            placeholder="e.g. Post-thunderstorm power dip, construction dust, high ambient humidity",
            help="Operating context that may explain electrical or mechanical drift.",
            key="widget_op_cond",
        )

        # ---------------------------------------------------------------------
        # Group B: Fault and sensor data
        # ---------------------------------------------------------------------
        st.markdown(
            "<div style='font-size: 0.88rem; font-weight: 700; color: #243247; margin-top: 16px; margin-bottom: 8px; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px;'>"
            "Fault and sensor data"
            "</div>",
            unsafe_allow_html=True,
        )

        st.text_input(
            "Additional Fault Codes (Optional)",
            placeholder="e.g. secondary DTCs: E-DR-202, FLT-14 (comma-separated)",
            help="Any secondary or historical trouble codes logged during the same event.",
            key="widget_extra_codes",
        )

        tab_upload, tab_editor = st.tabs(["Upload Telemetry File (CSV / JSON)", "Structured JSON Editor"])

        with tab_upload:
            up_col1, up_col2 = st.columns([1.8, 1.2])
            with up_col1:
                uploaded_file = st.file_uploader(
                    "Select Controller Log File",
                    type=["csv", "json"],
                    key="telemetry_uploader_widget",
                    help="Accepts CSV (tabular or key-value) and JSON formats up to 10 MB.",
                )
            with up_col2:
                if uploaded_file is not None:
                    is_valid, parsed_data, err_msg, meta = validate_and_parse_telemetry_upload(uploaded_file)
                    if is_valid:
                        st.session_state["uploaded_telemetry_data"] = parsed_data
                        st.success(f"**{meta['filename']}** verified. Parsed **{meta['parsed_count']}** sensor readings.")
                    else:
                        st.session_state["uploaded_telemetry_data"] = {}
                        st.error(f"**Upload Validation Failed**: {err_msg}")
                else:
                    st.caption("No file currently uploaded. Drag and drop or browse for a telemetry log.")
                    if st.session_state.get("uploaded_telemetry_data"):
                        if st.button("Clear Uploaded Data", icon=":material/delete:", key="btn_clear_uploaded_tel"):
                            st.session_state["uploaded_telemetry_data"] = {}
                            st.rerun()

            cached_upload = st.session_state.get("uploaded_telemetry_data", {})
            if cached_upload:
                st.markdown("##### Uploaded Telemetry Preview")
                df_tel = pd.DataFrame([
                    {
                        "Sensor Parameter": k.replace("_", " ").title(),
                        "Raw Key": k,
                        "Reading": v,
                        "Inferred Unit": DiagnosticEnricher._infer_telemetry_unit(k)[0],
                        "Nominal Range": DiagnosticEnricher._infer_telemetry_unit(k)[1],
                        "Condition": DiagnosticEnricher._assess_telemetry_reading(k, v),
                    }
                    for k, v in cached_upload.items()
                ])
                st.dataframe(df_tel, hide_index=True, use_container_width=True)

        with tab_editor:
            ed_c1, ed_c2 = st.columns([1.5, 1.5])
            with ed_c1:
                raw_editor_text = st.text_area(
                    "Telemetry JSON Structure",
                    value=st.session_state.get("manual_json_text", DEFAULT_JSON_EXAMPLE),
                    height=140,
                    key="manual_json_input_widget",
                    help="Key-value JSON object containing sensor readings and units.",
                )
                st.session_state["manual_json_text"] = raw_editor_text
                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    if st.button("Load Standard Example", icon=":material/refresh:", key="btn_load_ex"):
                        st.session_state["manual_json_text"] = DEFAULT_JSON_EXAMPLE
                        st.rerun()
                with btn_c2:
                    if st.button("Clear Editor", icon=":material/delete:", key="btn_clear_ed"):
                        st.session_state["manual_json_text"] = "{}"
                        st.rerun()

            with ed_c2:
                json_valid = False
                parsed_manual = {}
                json_err = None
                if raw_editor_text.strip():
                    try:
                        parsed_manual = json.loads(raw_editor_text)
                        if not isinstance(parsed_manual, dict):
                            json_err = "JSON root must be an object (dictionary with curly braces {})."
                        else:
                            json_valid = True
                    except json.JSONDecodeError as exc:
                        json_err = f"Syntax Error: {exc.msg} (line {exc.lineno}, col {exc.colno})"
                else:
                    json_valid = True
                    parsed_manual = {}

                if json_valid:
                    if parsed_manual:
                        st.markdown(
                            f"""
                            <div style="background-color: #EFF7F2; border: 1px solid #C6E2D3; border-left: 3px solid #3F7D62;
                                        border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
                                <span style="color: #3F7D62; font-weight: 700; font-size: 0.85rem;">Valid JSON Structure</span>
                                <div style="font-size: 0.8rem; color: #2D5845; margin-top: 2px;">
                                    Detected <b>{len(parsed_manual)}</b> sensor parameters ready for diagnostic evaluation.
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        st.json(parsed_manual, expanded=False)
                    else:
                        st.info("JSON editor is empty. Diagnosis will proceed using symptom matching only.")
                else:
                    st.markdown(
                        f"""
                        <div style="background-color: #FDF2F2; border: 1px solid #ECC4C4; border-left: 3px solid #B84C4C;
                                    border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
                            <span style="color: #B84C4C; font-weight: 700; font-size: 0.85rem;">JSON Syntax Invalid</span>
                            <div style="font-size: 0.78rem; color: #8C2F2F; margin-top: 2px;">{json_err}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        # ---------------------------------------------------------------------
        # Group C: Additional observations
        # ---------------------------------------------------------------------
        st.markdown(
            "<div style='font-size: 0.88rem; font-weight: 700; color: #243247; margin-top: 16px; margin-bottom: 8px; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px;'>"
            "Additional observations"
            "</div>",
            unsafe_allow_html=True,
        )

        st.text_area(
            "Technician Field Observations & Notes (Optional)",
            placeholder="e.g. Multimeter spot-checks, visual check on landing sills, recent maintenance findings",
            height=80,
            help="Multimeter spot-checks, tactile observations, or recent maintenance history.",
            key="widget_tech_notes",
        )

        st.text_area(
            "Detailed Problem Narrative (Optional)",
            placeholder="e.g. Plain-language incident narrative reported by facility staff (if different from symptoms)",
            height=72,
            help="Plain-language description of the incident reported by building staff or observed on arrival.",
            key="widget_addl_narrative",
        )

    # =========================================================================
    # Primary Action: Diagnose Fault
    # =========================================================================
    run_diagnose = st.button(
        "Diagnose Fault",
        icon=":material/bolt:",
        type="primary",
        use_container_width=True,
        key="btn_diagnose_fault_primary",
    )
    st.markdown(
        "<div style='text-align: center; color: #68778D; font-size: 0.84rem; margin-top: 6px; margin-bottom: 16px;'>"
        "Review the likely cause and recommended next steps."
        "</div>",
        unsafe_allow_html=True,
    )

    if run_diagnose:
        fault_code_val = st.session_state.get("widget_fault_code", "").strip()
        symptoms_text = st.session_state.get("widget_symptoms", "").strip()

        symptoms_list = [s.strip() for s in symptoms_text.replace(";", "\n").splitlines() if s.strip()]
        if not symptoms_list and not fault_code_val:
            st.error("Validation Error: Please enter a fault code or describe what is happening before diagnosing.")
            return

        if not symptoms_list:
            symptoms_list = [f"Elevator controller registered fault code {fault_code_val}"]

        # Consolidate equipment parameters from persistent session state
        raw_elv = st.session_state.get("widget_elv_id", "ELV-CAR-04")
        effective_elv_id = raw_elv.strip() if raw_elv and raw_elv.strip() else "ELV-UNSPECIFIED"

        raw_bldg = st.session_state.get("widget_bldg", "Commercial Plaza Tower B")
        effective_bldg = raw_bldg.strip() if raw_bldg and raw_bldg.strip() else None

        effective_mfg = st.session_state.get("widget_mfg", "Otis Elevator Company")

        raw_model = st.session_state.get("widget_model", "Geared Traction VVVF Passenger (Gen2)")
        effective_model = raw_model.strip() if raw_model and raw_model.strip() else "Generic / Unspecified"

        effective_subsystem = st.session_state.get("widget_subsystem", "door_system")
        effective_severity = st.session_state.get("widget_sev", "High — Service Interruption / Out of Service")

        raw_op_cond = st.session_state.get("widget_op_cond", "Morning peak dispatch; high ambient machine room humidity (82%), 31°C")
        effective_op_cond = raw_op_cond.strip() if raw_op_cond and raw_op_cond.strip() else "Normal Operating Conditions"

        # Consolidate technician notes and extra fault codes
        tech_notes_val = st.session_state.get("widget_tech_notes", "").strip()
        extra_codes_val = st.session_state.get("widget_extra_codes", "").strip()
        addl_narrative_val = st.session_state.get("widget_addl_narrative", "").strip()

        notes_parts = []
        if tech_notes_val:
            notes_parts.append(tech_notes_val)
        if extra_codes_val:
            notes_parts.append(f"Additional Fault Codes: {extra_codes_val}")
        combined_notes = "\n".join(notes_parts) if notes_parts else None

        prob_desc = addl_narrative_val if addl_narrative_val else (symptoms_list[0] if symptoms_list else "Elevator operational fault")

        # Consolidate active telemetry
        cached_up = st.session_state.get("uploaded_telemetry_data", {})
        manual_txt = st.session_state.get("manual_json_text", "").strip()
        active_telemetry = {}
        if cached_up:
            active_telemetry = cached_up
        elif manual_txt and manual_txt != "{}":
            try:
                parsed = json.loads(manual_txt)
                if isinstance(parsed, dict):
                    active_telemetry = parsed
            except Exception:
                active_telemetry = {}

        request = DiagnosisRequest(
            elevator_id=effective_elv_id,
            building_id=effective_bldg,
            subsystem=effective_subsystem,
            fault_code=fault_code_val if fault_code_val else None,
            symptoms=symptoms_list,
            telemetry=active_telemetry,
            technician_notes=combined_notes,
            manufacturer=effective_mfg,
            equipment_model=effective_model,
            problem_description=prob_desc,
            operating_conditions=effective_op_cond,
            severity=effective_severity,
        )

        engine = DiagnosisEngine(enable_verification=True)
        try:
            with st.spinner("Analyzing fault code, evaluating historical evidence, and isolating root cause..."):
                result = engine.analyze(request)

            # Persist session state
            st.session_state["current_investigation_id"] = result.investigation_id
            st.session_state["current_result"] = result
            st.session_state["saved_elv_id"] = effective_elv_id

            # Automatically route to Diagnostic Results for this investigation
            navigate_to("results", result.investigation_id)

        except Exception as exc:
            logger.error("Diagnostic execution failed: %s", exc, exc_info=True)
            st.error(f"Diagnostic Pipeline Error: {exc}. Please review inputs or check system logs.")
