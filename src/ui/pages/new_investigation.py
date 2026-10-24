"""New Investigation workflow page for elevator technician decision support."""

import csv
import io
import json
from pathlib import Path
from typing import Any, Dict
import streamlit as st

from fault_sense.schema import SubsystemType
from src.diagnosis.engine import DiagnosisEngine
from src.diagnosis.session import DiagnosisRequest
from src.utils.logger import get_logger

logger = get_logger(__name__)


def parse_telemetry_file(uploaded_file: Any) -> Dict[str, Any]:
    """Parses an uploaded CSV or JSON file into a telemetry dictionary."""
    content = uploaded_file.getvalue()
    filename = uploaded_file.name.lower()

    if filename.endswith(".json"):
        try:
            data = json.loads(content.decode("utf-8"))
            if isinstance(data, dict):
                return data
            elif isinstance(data, list) and data and isinstance(data[0], dict):
                return data[0]
            else:
                st.warning("JSON file did not contain a key-value telemetry object.")
                return {}
        except Exception as exc:
            st.warning(f"Error parsing telemetry JSON: {exc}. Using empty telemetry.")
            return {}

    elif filename.endswith(".csv"):
        try:
            text = content.decode("utf-8")
            reader = csv.reader(io.StringIO(text))
            rows = [r for r in reader if r and any(cell.strip() for cell in r)]
            if not rows:
                return {}

            def is_num(val_str: str) -> bool:
                try:
                    float(val_str.strip())
                    return True
                except (ValueError, TypeError):
                    return False

            # Check for key-value pair format
            # Case 1: 2 columns, row 0 column 1 is numeric (e.g. "voltage,680")
            is_kv_direct = len(rows[0]) == 2 and is_num(rows[0][1])
            # Case 2: 2 columns with header like "parameter,value" or "metric,reading"
            is_kv_header = len(rows[0]) == 2 and rows[0][0].lower() in ("parameter", "metric", "sensor", "name", "key")

            if is_kv_direct or is_kv_header:
                start_idx = 1 if is_kv_header else 0
                result = {}
                for r in rows[start_idx:]:
                    if len(r) >= 2 and r[0].strip():
                        val = r[1].strip()
                        try:
                            val = float(val) if "." in val else int(val)
                        except ValueError:
                            pass
                        result[r[0].strip()] = val
                return result

            # Otherwise tabular format: row 0 is headers, row 1+ is readings
            headers = [h.strip() for h in rows[0]]
            if len(rows) > 1:
                vals = [v.strip() for v in rows[1]]
                result = {}
                for h, v in zip(headers, vals):
                    try:
                        v_conv = float(v) if "." in v else int(v)
                    except ValueError:
                        v_conv = v
                    result[h] = v_conv
                return result
            return {}
        except Exception as exc:
            st.warning(f"Error parsing telemetry CSV: {exc}. Using empty telemetry.")
            return {}

    return {}


def render_new_investigation_page() -> None:
    """Renders the technician investigation interface and diagnostic output."""
    st.markdown("## 🔍 New Fault Investigation")
    st.markdown(
        "Enter observed elevator operational symptoms, telemetry alarms, or manufacturer fault codes to isolate root causes."
    )

    with st.form("investigation_form"):
        col1, col2 = st.columns(2)

        with col1:
            elevator_id = st.text_input(
                "Elevator Unit Identifier *",
                value="ELV-CAR-04",
                help="Unique car identification number, e.g. ELV-CAR-04, ELV-NORTH-01",
            )
            building_id = st.text_input(
                "Building / Job Site ID",
                value="Commercial Plaza Tower B",
                help="Building name or site identifier",
            )
            subsystem_options = [s.value for s in SubsystemType]
            subsystem = st.selectbox(
                "Suspected Subsystem *",
                options=subsystem_options,
                format_func=lambda x: x.replace("_", " ").title(),
                index=subsystem_options.index("door_system") if "door_system" in subsystem_options else 0,
            )

        with col2:
            fault_code = st.text_input(
                "Observed Fault Code (if any)",
                value="E-DR-201",
                help="OEM controller error code, e.g. E-DR-201, E-VFD-404, FLT-12",
            )
            symptoms_input = st.text_area(
                "Observed Symptoms (one per line or semicolon-separated) *",
                value="Car door reopens repeatedly without passenger obstruction\nDoor dwell timer buzzer sounding",
                height=110,
                help="Describe abnormal physical sensations, noises, leveling errors, or door behavior.",
            )

        st.markdown("#### 📡 Physical Telemetry & Sensor Readings (Optional)")
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            uploaded_telemetry = st.file_uploader(
                "Upload Telemetry File (CSV or JSON)",
                type=["csv", "json"],
                help="Upload real-time controller logs or sensor exports.",
            )
        with t_col2:
            telemetry_raw = st.text_area(
                "Manual Telemetry Readings (JSON format)",
                value='{\n  "door_open_close_cycles": 142500,\n  "curtain_optical_attenuation_db": 6.8,\n  "motor_current_peak_a": 3.8\n}',
                height=100,
                help="Enter direct key-value sensor observations if no file is available.",
            )

        technician_notes = st.text_input(
            "Technician Field Notes (Optional)",
            value="Initial visual check performed on landing sills.",
            help="Notes on physical inspections, environmental conditions, or prior service history.",
        )

        submitted = st.form_submit_button("⚡ Run Fault Isolation & RCA", type="primary", use_container_width=True)

    if submitted:
        # Validation checks
        if not elevator_id.strip():
            st.error("Validation Error: Please specify the Elevator Unit Identifier.", icon="🚨")
            return

        symptoms = [s.strip() for s in symptoms_input.replace(";", "\n").splitlines() if s.strip()]
        if not symptoms:
            st.error("Validation Error: At least one observed symptom must be provided.", icon="🚨")
            return

        # Parse telemetry
        telemetry: Dict[str, Any] = {}
        if uploaded_telemetry is not None:
            telemetry = parse_telemetry_file(uploaded_telemetry)
            if telemetry:
                st.info(f"Loaded **{len(telemetry)}** sensor readings from uploaded file `{uploaded_telemetry.name}`.")
        elif telemetry_raw.strip():
            try:
                telemetry = json.loads(telemetry_raw)
            except Exception as exc:
                st.warning(f"Telemetry JSON syntax invalid ({exc}). Proceeding without telemetry.")
                telemetry = {}

        request = DiagnosisRequest(
            elevator_id=elevator_id.strip(),
            building_id=building_id.strip() if building_id else None,
            subsystem=subsystem,
            fault_code=fault_code.strip() if fault_code else None,
            symptoms=symptoms,
            telemetry=telemetry,
            technician_notes=technician_notes.strip() if technician_notes else None,
        )

        engine = DiagnosisEngine(enable_verification=True)
        try:
            with st.spinner("Retrieving evidence package, running diagnostic reasoning, and verifying grounding..."):
                result = engine.analyze(request)

            # Persist active investigation ID in session state
            st.session_state["current_investigation_id"] = result.investigation_id
            st.session_state["current_result"] = result

            st.success(f"Investigation **{result.investigation_id}** completed and saved to persistent audit storage!")

            # Quick summary header
            c_score, c_suff, c_verif, c_btn = st.columns([1, 1, 1, 1.5])
            with c_score:
                st.metric("Advisory Confidence", f"{int(result.confidence_score * 100)}%")
            with c_suff:
                st.metric("Sufficiency", result.sufficiency_level.upper())
            with c_verif:
                v_badge = "✅ Verified" if result.is_verified else "⏳ Inconclusive"
                st.metric("Verification", v_badge, delta=f"Retries: {result.retry_count}")
            with c_btn:
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                if st.button("👉 Open Full Report & Historical Citations", type="primary", use_container_width=True):
                    st.session_state["nav_page"] = "results"
                    st.rerun()

            # Primary hypothesis callout
            st.markdown(
                f"""
                <div style="background-color: #131F37; border-left: 4px solid #06B6D4; padding: 14px 18px; border-radius: 6px; margin: 12px 0;">
                    <div style="font-size: 0.78rem; font-weight: 700; color: #38BDF8; text-transform: uppercase;">
                        Synthesized Primary Root Cause
                    </div>
                    <div style="font-size: 1.05rem; color: #F8FAFC; margin-top: 6px; font-weight: 600;">
                        {result.root_cause_hypothesis}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        except Exception as exc:
            logger.error("Diagnostic execution failed: %s", exc, exc_info=True)
            st.error(f"Diagnostic Engine Error: {exc}. Please check system logs.", icon="🚨")
