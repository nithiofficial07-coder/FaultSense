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


def render_new_investigation_page() -> None:
    """Renders the comprehensive technician investigation workflow."""
    st.markdown(
        "Initiate an evidence-grounded root-cause analysis by entering observed operational symptoms, "
        "OEM diagnostic trouble codes, and physical controller telemetry."
    )

    # Initialize investigation state containers
    if "telemetry_input_mode" not in st.session_state:
        st.session_state["telemetry_input_mode"] = "file"
    if "uploaded_telemetry_data" not in st.session_state:
        st.session_state["uploaded_telemetry_data"] = {}
    if "manual_json_text" not in st.session_state:
        st.session_state["manual_json_text"] = DEFAULT_JSON_EXAMPLE
    if "auto_incident_id" not in st.session_state:
        st.session_state["auto_incident_id"] = f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{int(time.time()) % 10000:04d}"

    # Preset Quick-Load Selector
    with st.expander("Load Pre-configured Field Failure Scenario (Benchmark Presets)", expanded=False):
        c_scen, c_load, c_reset = st.columns([2.5, 1.2, 1.2])
        with c_scen:
            selected_preset_name = st.selectbox(
                "Select Failure Scenario Benchmark",
                options=list(SYMPTOM_PRESETS.keys()),
            )
        with c_load:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("Apply Scenario Preset", icon=":material/check:", use_container_width=True, key="btn_apply_preset"):
                preset_data = SYMPTOM_PRESETS[selected_preset_name]
                sub = preset_data[0]
                code = preset_data[1]
                syms = preset_data[2]
                notes = preset_data[3]
                desc = preset_data[4] if len(preset_data) > 4 else syms.splitlines()[0]
                telem_json = preset_data[5] if len(preset_data) > 5 else "{}"

                st.session_state["subsystem_picker"] = sub
                st.session_state["subsystem_select"] = sub
                st.session_state["fault_code_field"] = code
                st.session_state["fault_code_input"] = code
                st.session_state["symptoms_field"] = syms
                st.session_state["symptoms_input"] = syms
                st.session_state["notes_field"] = notes
                st.session_state["notes_input"] = notes
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
                st.session_state["subsystem_picker"] = "door_system"
                st.session_state["subsystem_select"] = "door_system"
                st.session_state["fault_code_field"] = ""
                st.session_state["fault_code_input"] = ""
                st.session_state["symptoms_field"] = ""
                st.session_state["symptoms_input"] = ""
                st.session_state["notes_field"] = ""
                st.session_state["notes_input"] = ""
                st.session_state["problem_desc_field"] = ""
                st.session_state["manual_json_text"] = "{}"
                st.session_state["uploaded_telemetry_data"] = {}
                st.session_state["current_result"] = None
                st.rerun()

    # =========================================================================
    # Section 1: Equipment & Incident Identification
    # =========================================================================
    st.markdown("### 1. Equipment & Incident Identification")
    st.caption("Identify the affected vertical transportation asset, manufacturer, model, and operating conditions.")

    c1, c2, c3 = st.columns(3)
    with c1:
        incident_id = st.text_input(
            "Incident / Work Order ID",
            value=st.session_state.get("auto_incident_id"),
            disabled=True,
            help="Automatically generated unique field ticket identifier.",
        )
        elevator_id = st.text_input(
            "Elevator Unit Identifier",
            value=st.session_state.get("saved_elv_id", "ELV-CAR-04"),
            placeholder="e.g. ELV-CAR-04, UNIT-B (optional / if available)",
            help="Unique equipment ID assigned by building management or OEM (defaults to ELV-UNSPECIFIED if left blank).",
        )

    with c2:
        mfg_options = [
            "Otis Elevator Company",
            "Schindler Group",
            "KONE Corporation",
            "TK Elevator (Thyssenkrupp)",
            "Mitsubishi Electric",
            "Fujitec",
            "Generic / Other Manufacturer",
        ]
        manufacturer = st.selectbox(
            "Elevator Manufacturer (if known)",
            options=mfg_options,
            index=0,
            help="OEM manufacturer specification helps contextualize schematics and code limits.",
        )
        elevator_model = st.text_input(
            "Elevator Model / Drive Type (if known)",
            value="Geared Traction VVVF Passenger (Gen2)",
            placeholder="e.g. 3300 MRL, MonoSpace, TAC32",
            help="Controller family or drive architecture.",
        )

    with c3:
        building_id = st.text_input(
            "Building / Job Site ID",
            value="Commercial Plaza Tower B",
            placeholder="e.g. Metropolitan Medical Center",
            help="Facility name, campus, or physical site location.",
        )
        severity = st.selectbox(
            "Incident Severity & Urgency Assessment",
            options=[
                "High — Service Interruption / Out of Service",
                "Critical — Safety Circuit Trip / Passenger Entrapment",
                "Medium — Intermittent Fault / Degraded Ride",
                "Low — Routine Preventive Maintenance Finding",
            ],
            index=0,
        )

    operating_conditions = st.text_input(
        "Operating & Environmental Conditions (Optional)",
        value="Morning peak dispatch; high ambient machine room humidity (82%), 31°C",
        placeholder="e.g. Post-thunderstorm power dip, construction dust in hoistway, cold weather start",
        help="Operating context that may explain electrical or mechanical drift.",
    )

    st.markdown("<hr style='margin: 14px 0; border: 0; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)

    # =========================================================================
    # Section 2: Fault Indicators & Observed Symptoms
    # =========================================================================
    st.markdown("### 2. Fault Indicators & Observed Symptoms")
    st.caption("Specify the affected subsystem, narrative problem description, controller DTC error codes, and technician observations.")

    s_col1, s_col2 = st.columns([1, 1.4])
    with s_col1:
        subsystem_options = [s.value for s in SubsystemType]
        default_sub = st.session_state.get("subsystem_select", "door_system")
        sub_idx = subsystem_options.index(default_sub) if default_sub in subsystem_options else 0
        subsystem = st.selectbox(
            "Affected Subsystem *",
            options=subsystem_options,
            format_func=lambda x: x.replace("_", " ").title(),
            index=sub_idx,
            key="subsystem_picker",
            help="Primary physical subsystem exhibiting anomalous behavior.",
        )

        fault_code = st.text_input(
            "OEM Controller Fault Code (DTC) (if registered)",
            value=st.session_state.get("fault_code_field", st.session_state.get("fault_code_input", "E-DR-201")),
            placeholder="e.g. E-DR-201, E-VFD-404, FLT-12 (leave blank if none)",
            key="fault_code_field",
            help="Diagnostic trouble code logged in controller fault history buffer.",
        )

        technician_notes = st.text_area(
            "Technician Field Observations & Notes (Optional)",
            value=st.session_state.get("notes_field", st.session_state.get("notes_input", "Initial visual check performed on landing sills. No large physical obstruction visible.")),
            height=78,
            key="notes_field",
            help="Multimeter spot-checks, tactile observations, or recent maintenance history.",
        )

    with s_col2:
        problem_description = st.text_area(
            "Problem Description / Incident Narrative *",
            value=st.session_state.get("problem_desc_field", "Elevator car doors cycling open and closed repeatedly at Floor 4 without passenger obstruction, preventing departure."),
            height=75,
            key="problem_desc_field",
            help="Plain-language description of the problem reported by building staff or observed on arrival.",
        )

        default_syms = st.session_state.get(
            "symptoms_field",
            st.session_state.get(
                "symptoms_input",
                "Car door reopens repeatedly without passenger obstruction\nDoor dwell timer expires causing nudging buzzer activation\nIntermittent reopening at intermediate floors",
            ),
        )
        symptoms_input = st.text_area(
            "Observed Operational Symptoms * (One per line or semicolon-separated)",
            value=default_syms,
            height=100,
            key="symptoms_field",
            help="Specific physical anomalies: e.g. door bounce, shudder, leveling drift, abnormal acoustic pitch.",
        )

    # Missing Information Assessment Callout
    missing_items = []
    if not fault_code.strip():
        missing_items.append("OEM Fault Code (DTC) is missing (will rely on symptom matching)")
    if "Generic" in manufacturer:
        missing_items.append("Manufacturer/Model is generic (schematic pinouts must be verified on-site)")
    if not elevator_id.strip():
        missing_items.append("Unit ID is blank (will default to ELV-UNSPECIFIED)")

    if missing_items:
        st.markdown(
            f"""
            <div style="background-color: #FDF8EE; border: 1px solid #EED8B4; border-left: 3px solid #A8752B; padding: 10px 14px; border-radius: 8px; margin-bottom: 8px; font-size: 0.8rem; color: #7D561F;">
                <b>Diagnostic Precision Advisory</b>: {'; '.join(missing_items)}. FaultSense will analyze available data without fabricating missing specifications.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<hr style='margin: 14px 0; border: 0; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)

    # =========================================================================
    # Section 3: Physical Telemetry & Sensor Readings
    # =========================================================================
    st.markdown("### 3. Physical Telemetry & Sensor Readings")
    st.markdown(
        "<div style='color: #68778D; font-size: 0.85rem; margin-bottom: 10px;'>"
        "Provide controller telemetry data through either an <b>uploaded data file</b> or the <b>structured JSON editor</b>. "
        "Telemetry enables grounding against quantitative sensor thresholds."
        "</div>",
        unsafe_allow_html=True,
    )

    tab_upload, tab_editor = st.tabs(["Method A: Upload Telemetry File (CSV / JSON)", "Method B: Structured JSON Editor"])

    active_telemetry: Dict[str, Any] = {}

    with tab_upload:
        st.markdown(
            "Upload an exported CSV or JSON telemetry recording. Files are validated immediately upon selection."
        )
        up_col1, up_col2 = st.columns([1.8, 1.2])

        with up_col1:
            uploaded_file = st.file_uploader(
                "Select Controller Log File",
                type=["csv", "json"],
                key="telemetry_uploader_widget",
                help="Accepts CSV (tabular or key-value) and JSON (object) formats up to 10 MB.",
            )

        with up_col2:
            if uploaded_file is not None:
                is_valid, parsed_data, err_msg, meta = validate_and_parse_telemetry_upload(uploaded_file)
                if is_valid:
                    st.session_state["uploaded_telemetry_data"] = parsed_data
                    st.success(
                        f"**{meta['filename']}** verified. Parsed **{meta['parsed_count']}** sensor readings "
                        f"({meta['size_bytes']} bytes, {meta['format']})."
                    )
                else:
                    st.session_state["uploaded_telemetry_data"] = {}
                    st.error(f"**Upload Validation Failed**: {err_msg}")
            else:
                st.caption("No file currently uploaded. Drag and drop or browse for a controller telemetry log.")
                if st.session_state.get("uploaded_telemetry_data"):
                    if st.button("Clear Cached Uploaded Data", icon=":material/delete:"):
                        st.session_state["uploaded_telemetry_data"] = {}
                        st.rerun()

        # Telemetry preview table if file is active
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
        st.markdown(
            "Enter sensor measurements directly as a valid JSON object. Numerical values are cross-checked."
        )

        ed_c1, ed_c2 = st.columns([1.5, 1.5])
        with ed_c1:
            raw_editor_text = st.text_area(
                "Telemetry JSON Structure",
                value=st.session_state.get("manual_json_text", DEFAULT_JSON_EXAMPLE),
                height=150,
                key="manual_json_input_widget",
                help="Key-value JSON object containing sensor readings and units.",
            )

            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("Load Standard Example", icon=":material/refresh:", key="btn_load_ex"):
                    st.session_state["manual_json_text"] = DEFAULT_JSON_EXAMPLE
                    st.rerun()
            with btn_col2:
                if st.button("Clear Editor", icon=":material/delete:", key="btn_clear_ed"):
                    st.session_state["manual_json_text"] = "{}"
                    st.rerun()

        with ed_c2:
            # Live validation of manual JSON
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

    # Determine consolidated telemetry to feed into diagnostic pipeline
    if cached_upload:
        active_telemetry = cached_upload
        active_source = "Uploaded Log File"
    elif json_valid and parsed_manual:
        active_telemetry = parsed_manual
        active_source = "Manual JSON Editor"
    else:
        active_telemetry = {}
        active_source = "None (Symptom Matching Only)"

    st.caption(f"Active Telemetry Source for Diagnosis: **{active_source}** ({len(active_telemetry)} readings).")

    st.markdown("<hr style='margin: 16px 0; border: 0; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)

    # =========================================================================
    # Section 4: Run Diagnostic Investigation
    # =========================================================================
    st.markdown("### 4. Execute Diagnostic Pipeline")

    run_submitted = st.button(
        "Run Fault Isolation & Self-Verification Analysis",
        icon=":material/bolt:",
        type="primary",
        use_container_width=True,
        key="btn_run_diagnosis_main",
    )

    if run_submitted:
        # Normalize elevator ID (default if blank)
        effective_elv_id = elevator_id.strip() if elevator_id.strip() else "ELV-UNSPECIFIED"

        symptoms = [s.strip() for s in symptoms_input.replace(";", "\n").splitlines() if s.strip()]
        if not symptoms:
            st.error("Validation Error: At least one observed symptom must be provided.")
            return

        # Build formal diagnosis request with all equipment & operating context
        request = DiagnosisRequest(
            elevator_id=effective_elv_id,
            building_id=building_id.strip() if building_id else None,
            subsystem=subsystem,
            fault_code=fault_code.strip() if fault_code else None,
            symptoms=symptoms,
            telemetry=active_telemetry,
            technician_notes=technician_notes.strip() if technician_notes else None,
            manufacturer=manufacturer,
            equipment_model=elevator_model.strip() if elevator_model else "Generic / Unspecified",
            problem_description=problem_description.strip() if problem_description else (symptoms[0] if symptoms else "Elevator operational fault"),
            operating_conditions=operating_conditions.strip() if operating_conditions else "Normal Operating Conditions",
            severity=severity,
        )

        engine = DiagnosisEngine(enable_verification=True)
        repo = InvestigationRepository()
        kb_manager = KnowledgeBaseManager()

        try:
            with st.spinner("Retrieving historical evidence, evaluating candidate causes, and executing verification loop..."):
                result = engine.analyze(request)

            # Persist session state
            st.session_state["current_investigation_id"] = result.investigation_id
            st.session_state["current_result"] = result
            st.session_state["saved_elv_id"] = effective_elv_id

            st.success(
                f"Diagnostic Session **{result.investigation_id}** completed and saved to persistent audit database!"
            )

            # Fetch enriched record from database
            saved_rec = repo.get(result.investigation_id) or result.to_dict()
            dossier = DiagnosticEnricher.enrich_investigation(saved_rec, kb_manager=kb_manager)

            # Executive Results Banner with Evidence-Based Status
            verif_badge = dossier.evidence_based_status
            c_score, c_verif, c_retry, c_cases = st.columns(4)
            with c_score:
                st.metric(
                    "Advisory Confidence",
                    f"{int(result.confidence_score * 100)}%",
                    help="Empirical evidence support score based on semantic similarity, DTC alignment, symptom overlap, sensor telemetry, and corroboration (NOT a calibrated statistical probability).",
                )
            with c_verif:
                st.metric("Diagnostic Status", verif_badge)
            with c_retry:
                if result.retry_count == 0 and result.is_verified:
                    retry_label = "0 (Passed 1st Step)"
                elif result.retry_count > 0:
                    retry_label = f"{result.retry_count} retries ({result.retry_count + 1} steps)"
                else:
                    retry_label = "0 retries (Unverified)"
                st.metric("Verification Retries", retry_label)
            with c_cases:
                st.metric("Matched Evidence Cases", str(len(result.matched_cases)))

            # Evidence Support Score Factor Breakdown Expander
            bd = result.confidence_breakdown or getattr(dossier, "confidence_breakdown", None) or {}
            if bd:
                with st.expander("Evidence Support Score & Factor Breakdown", expanded=False):
                    f1, f2, f3, f4, f5 = st.columns(5)
                    with f1:
                        st.caption("Semantic Match")
                        st.write(f"**{int(bd.get('semantic_component', 0) * 100 / 0.35)}%** (wt: 35%)")
                    with f2:
                        st.caption("DTC Code Match")
                        dtc_match = "Matched" if bd.get("exact_fault_code_match") else "No Match"
                        st.write(f"**{dtc_match}** ({int(bd.get('fault_code_component', 0) * 100)}%)")
                    with f3:
                        st.caption("Symptom Overlap")
                        st.write(f"**{int(bd.get('symptom_overlap_ratio', 0) * 100)}%** (wt: 22%)")
                    with f4:
                        st.caption("Sensor Telemetry")
                        telem_stat = "Validated" if bd.get("telemetry_provided") else "Missing"
                        st.write(f"**{telem_stat}**")
                    with f5:
                        st.caption("Corroboration")
                        st.write(f"**{bd.get('corroboration_count', 0)} case(s)**")

                    if bd.get("penalties_applied"):
                        st.markdown("**Evidence Gaps & Penalties:**")
                        for p in bd["penalties_applied"]:
                            st.markdown(f"- *{p}*")
                    if bd.get("scoring_notes"):
                        st.caption(f"**Scoring Logic**: {bd['scoring_notes']}")

            # Primary Root Cause Card
            st.markdown(
                f"""
                <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid #4169A8;
                            padding: 16px 20px; border-radius: 10px; margin: 16px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                    <div style="font-size: 0.75rem; font-weight: 700; color: #4169A8; text-transform: uppercase; letter-spacing: 0.6px;">
                        Synthesized Primary Root Cause Hypothesis
                    </div>
                    <div style="font-size: 1.15rem; color: #243247; margin-top: 6px; font-weight: 700; line-height: 1.4;">
                        {result.root_cause_hypothesis}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Prominent PDF Download & JSON Export Block
            st.markdown("##### Download Official Investigation Artifacts")
            dl_col1, dl_col2 = st.columns([1.6, 1.2])

            with dl_col1:
                try:
                    pdf_bytes = DiagnosticReportGenerator.generate_pdf(saved_rec, kb_manager=kb_manager)
                    st.download_button(
                        label="Download Complete Diagnostic Report (PDF)",
                        icon=":material/description:",
                        data=pdf_bytes,
                        file_name=f"FaultSense_Report_{result.investigation_id}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True,
                        key=f"new_inv_pdf_{result.investigation_id}",
                    )
                    st.caption(f"Publication-grade multi-page PDF ready ({len(pdf_bytes) / 1024:.1f} KB). Includes 8 formal engineering sections.")
                except Exception as p_err:
                    logger.error("PDF generation on new_investigation failed: %s", p_err)
                    st.error(f"PDF generation error: {p_err}. You can retry or download from Diagnostic Results tab.")

            with dl_col2:
                try:
                    json_str = DiagnosticReportGenerator.generate_json(saved_rec, kb_manager=kb_manager)
                    st.download_button(
                        label="Export Structured JSON Data",
                        icon=":material/download:",
                        data=json_str,
                        file_name=f"FaultSense_Data_{result.investigation_id}.json",
                        mime="application/json",
                        type="secondary",
                        use_container_width=True,
                        key=f"new_inv_json_{result.investigation_id}",
                    )
                    st.caption("Complete 18-point machine-readable JSON dossier.")
                except Exception:
                    pass

            st.markdown("<hr style='margin: 12px 0; border: 0; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)

            # Direct Navigation Actions
            act_col1, act_col2, act_col3 = st.columns([1.4, 1.2, 1.2])
            with act_col1:
                if st.button("Dedicated Report Page", icon=":material/description:", key="btn_goto_rep", type="primary", use_container_width=True):
                    navigate_to("report", result.investigation_id)

            with act_col2:
                if st.button("View Full Audit Dossier", icon=":material/analytics:", key="btn_goto_res", type="secondary", use_container_width=True):
                    navigate_to("results", result.investigation_id)

            with act_col3:
                if st.button("Consult Assistant", icon=":material/chat:", key="btn_goto_chat", type="secondary", use_container_width=True):
                    navigate_to("assistant", result.investigation_id)

        except Exception as exc:
            logger.error("Diagnostic execution failed: %s", exc, exc_info=True)
            st.error(f"Diagnostic Pipeline Error: {exc}. Please check system logs.")
