"""Investigation history page displaying past diagnosis sessions with filters, search, and direct PDF export in enterprise light theme."""

from __future__ import annotations

import json
import streamlit as st

from fault_sense.schema import SubsystemType
from src.knowledge_base.manager import KnowledgeBaseManager
from src.storage.repository import InvestigationRepository
from src.ui.components.sidebar import navigate_to
from src.utils.report_generator import DiagnosticReportGenerator


def render_history_page() -> None:
    """Renders the historical audit log of technician diagnostic sessions with filters and export."""
    st.markdown(
        "Search and review past elevator fault investigations, verification outcomes, evidence citations, "
        "and download authoritative engineering reports."
    )

    repo = InvestigationRepository()
    records = repo.list_all(limit=100)

    if not records:
        st.info("No investigation sessions recorded yet. Launch a diagnosis from **New Investigation**.")
        if st.button("Start First Investigation", icon=":material/search:", type="primary"):
            navigate_to("new_investigation")
        return

    # Filters Row
    f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
    with f_col1:
        search_kw = st.text_input(
            "Search investigations",
            value="",
            placeholder="Search by elevator ID, fault code, symptom, or root cause...",
            key="hist_search_box",
        ).lower().strip()

    with f_col2:
        subsystem_options = ["All Subsystems"] + [s.value for s in SubsystemType]
        sub_filter = st.selectbox(
            "Filter Subsystem",
            options=subsystem_options,
            format_func=lambda x: "All Subsystems" if x == "All Subsystems" else x.replace("_", " ").title(),
            key="hist_sub_filter",
        )

    with f_col3:
        status_filter = st.selectbox(
            "Filter Status",
            options=["All Statuses", "Completed / Grounded", "Inconclusive", "Open"],
            key="hist_status_filter",
        )

    # Apply filters
    filtered = []
    for r in records:
        if sub_filter != "All Subsystems" and r.get("subsystem") != sub_filter:
            continue

        status = r.get("status", "open")
        if status_filter == "Completed / Grounded" and status != "completed":
            continue
        elif status_filter == "Inconclusive" and status != "inconclusive":
            continue
        elif status_filter == "Open" and status != "open":
            continue

        if search_kw:
            searchable_blob = (
                f"{r.get('investigation_id', '')} "
                f"{r.get('elevator_id', '')} "
                f"{r.get('manufacturer', '')} "
                f"{r.get('equipment_model', '')} "
                f"{r.get('fault_code', '')} "
                f"{r.get('subsystem', '')} "
                f"{r.get('severity', '')} "
                f"{r.get('root_cause_hypothesis', '')} "
                f"{' '.join(r.get('symptoms', []))}"
            ).lower()
            if search_kw not in searchable_blob:
                continue

        filtered.append(r)

    st.caption(f"Showing **{len(filtered)}** of **{len(records)}** total recorded investigations.")

    if not filtered:
        st.info("No investigations match your search and filter criteria.")
        return

    kb_manager = KnowledgeBaseManager()

    # Render filtered records
    for rec in filtered:
        inv_id = rec.get("investigation_id", "Unknown")
        elv_id = rec.get("elevator_id", "Unknown")
        mfg = rec.get("manufacturer") or "Generic OEM"
        model = rec.get("equipment_model") or "Standard"
        sub = str(rec.get("subsystem", "")).replace("_", " ").title()
        conf = int(float(rec.get("confidence_score", 0.0)) * 100)
        status = rec.get("status", "open")
        sev = str(rec.get("severity", "medium")).capitalize()
        ts = rec.get("created_at", "")[:19].replace("T", " ")
        retries = rec.get("retry_count", 0)

        # Evidence-based status
        ev_status = rec.get("diagnostic_status") or rec.get("evidence_based_status")
        if not ev_status:
            verif_rec = rec.get("verification_record") or {}
            final_verdict = verif_rec.get("final_verdict", "sufficient" if status == "completed" else "inconclusive")
            if final_verdict == "sufficient" or status == "completed":
                ev_status = "Evidence Supported"
            else:
                ev_status = "Review Required"

        if "Supported" in ev_status or "Verified" in ev_status:
            badge_color = "#15803D"
        elif "Review" in ev_status or "Technician" in ev_status:
            badge_color = "#2563EB"
        elif "Insufficient" in ev_status:
            badge_color = "#64748B"
        else:
            badge_color = "#B45309"

        header = f"**{inv_id}** — Unit: `{elv_id}` ({mfg} {model}) [{sub}] | {sev} | {ts}"

        with st.expander(header):
            c1, c2 = st.columns([2.5, 1.5])
            with c1:
                st.markdown(f"**Synthesized Root Cause**:\n{rec.get('root_cause_hypothesis', 'N/A')}")
                if rec.get("problem_description"):
                    st.caption(f"**Reported Problem**: {rec.get('problem_description')}")
                st.markdown(f"**Documented Corrective Actions**:\n{rec.get('recommended_actions', 'N/A')}")
                if rec.get("symptoms"):
                    st.caption(f"Reported Symptoms: {', '.join(rec.get('symptoms'))}")

            with c2:
                st.markdown(f"**Equipment**: {mfg} {model}")
                st.markdown(f"**Building**: {rec.get('building_id') or 'N/A'}")
                st.markdown(f"**Fault Code**: `{rec.get('fault_code') or 'None'}`")
                st.markdown(f"<span style='color: {badge_color}; font-weight: 700;'>● {ev_status}</span>", unsafe_allow_html=True)
                st.caption(f"Advisory Confidence: {conf}% | Retries: {retries}")
                if rec.get("technician_notes"):
                    st.markdown(f"**Field Notes**: {rec.get('technician_notes')}")

            # Evidence citations
            matched_cases = rec.get("matched_case_ids", [])
            if matched_cases:
                cites_html = " ".join(f"<code style='color: #2563EB; background: #EFF6FF; border: 1px solid #BFDBFE; padding: 1px 4px; border-radius: 4px;'>{cid}</code>" for cid in matched_cases)
                st.markdown(f"**Evidence Citations**: {cites_html}", unsafe_allow_html=True)

            st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)

            # Quick Action & Direct Download Buttons
            btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([1.2, 1.2, 1.4, 1.2])
            with btn_col1:
                if st.button("Open in Results", key=f"hist_open_{inv_id}", icon=":material/analytics:", type="primary", use_container_width=True):
                    navigate_to("results", inv_id)
            with btn_col2:
                if st.button("Ask in Assistant", key=f"hist_chat_{inv_id}", icon=":material/chat:", type="secondary", use_container_width=True):
                    navigate_to("assistant", inv_id)
            with btn_col3:
                try:
                    pdf_data = DiagnosticReportGenerator.generate_pdf(rec, kb_manager=kb_manager)
                    st.download_button(
                        label="Download PDF Report",
                        icon=":material/description:",
                        data=pdf_data,
                        file_name=f"FaultSense_Report_{inv_id}.pdf",
                        mime="application/pdf",
                        key=f"hist_pdf_{inv_id}",
                        use_container_width=True,
                    )
                except Exception as exc:
                    st.caption(f"PDF generation error: {exc}")
            with btn_col4:
                try:
                    json_data = DiagnosticReportGenerator.generate_json(rec, kb_manager=kb_manager)
                    st.download_button(
                        label="Export JSON",
                        icon=":material/download:",
                        data=json_data,
                        file_name=f"FaultSense_Data_{inv_id}.json",
                        mime="application/json",
                        key=f"hist_json_{inv_id}",
                        use_container_width=True,
                    )
                except Exception:
                    pass
