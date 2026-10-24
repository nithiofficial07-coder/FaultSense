"""Investigation history page displaying past diagnosis sessions with filters, search, and export."""

import json
import streamlit as st

from fault_sense.schema import SubsystemType
from src.storage.repository import InvestigationRepository


def render_history_page() -> None:
    """Renders the historical audit log of technician diagnostic sessions with filters and export."""
    st.markdown("## 📋 Investigation History & Audit Log")
    st.markdown(
        "Search and review past elevator fault investigations, verification outcomes, evidence citations, and technician notes."
    )

    repo = InvestigationRepository()
    records = repo.list_all(limit=100)

    if not records:
        st.info("No investigation sessions recorded yet. Launch a diagnosis from **New Investigation**.", icon="ℹ️")
        if st.button("🚀 Start First Investigation", type="primary"):
            st.session_state["nav_page"] = "new_investigation"
            st.rerun()
        return

    # Filters Row
    f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
    with f_col1:
        search_kw = st.text_input(
            "Search investigations",
            value="",
            placeholder="Search by elevator ID, fault code, symptom, or root cause...",
        ).lower().strip()

    with f_col2:
        subsystem_options = ["All Subsystems"] + [s.value for s in SubsystemType]
        sub_filter = st.selectbox(
            "Filter Subsystem",
            options=subsystem_options,
            format_func=lambda x: "All Subsystems" if x == "All Subsystems" else x.replace("_", " ").title(),
        )

    with f_col3:
        status_filter = st.selectbox(
            "Filter Status",
            options=["All Statuses", "Completed / Grounded", "Inconclusive", "Open"],
        )

    # Apply filters
    filtered = []
    for r in records:
        # Subsystem filter
        if sub_filter != "All Subsystems" and r.get("subsystem") != sub_filter:
            continue

        # Status filter
        status = r.get("status", "open")
        if status_filter == "Completed / Grounded" and status != "completed":
            continue
        elif status_filter == "Inconclusive" and status != "inconclusive":
            continue
        elif status_filter == "Open" and status != "open":
            continue

        # Search keyword
        if search_kw:
            searchable_blob = (
                f"{r.get('investigation_id', '')} "
                f"{r.get('elevator_id', '')} "
                f"{r.get('fault_code', '')} "
                f"{r.get('subsystem', '')} "
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

    # Render filtered records
    for rec in filtered:
        inv_id = rec.get("investigation_id", "Unknown")
        elv_id = rec.get("elevator_id", "Unknown")
        sub = str(rec.get("subsystem", "")).replace("_", " ").title()
        conf = int(float(rec.get("confidence_score", 0.0)) * 100)
        status = rec.get("status", "open")
        ts = rec.get("created_at", "")[:19].replace("T", " ")
        retries = rec.get("retry_count", 0)

        # Verification badge
        verif_rec = rec.get("verification_record") or {}
        final_verdict = verif_rec.get("final_verdict", "sufficient" if status == "completed" else "inconclusive")
        is_verified = (final_verdict == "sufficient" or status == "completed")
        badge_color = "#34D399" if is_verified else "#F59E0B"
        badge_text = "VERIFIED" if is_verified else "INCONCLUSIVE"

        header = f"**{inv_id}** — Elevator: `{elv_id}` [{sub}] | Confidence: {conf}% | {ts}"

        with st.expander(header):
            c1, c2 = st.columns([2.5, 1.5])
            with c1:
                st.markdown(f"**Synthesized Root Cause**:\n{rec.get('root_cause_hypothesis', 'N/A')}")
                st.markdown(f"**Documented Corrective Actions**:\n{rec.get('recommended_actions', 'N/A')}")
                if rec.get("symptoms"):
                    st.caption(f"Reported Symptoms: {', '.join(rec.get('symptoms'))}")

            with c2:
                st.markdown(f"**Building**: {rec.get('building_id') or 'N/A'}")
                st.markdown(f"**Fault Code**: `{rec.get('fault_code') or 'None'}`")
                st.markdown(f"<span style='color: {badge_color}; font-weight: 700;'>● Verification: {badge_text}</span>", unsafe_allow_html=True)
                st.caption(f"Verification Retries: {retries}")
                if rec.get("technician_notes"):
                    st.markdown(f"**Field Notes**: {rec.get('technician_notes')}")

            # Evidence citations
            matched_cases = rec.get("matched_case_ids", [])
            if matched_cases:
                cites_html = " ".join(f"<code style='color: #38BDF8;'>{cid}</code>" for cid in matched_cases)
                st.markdown(f"**Evidence Citations**: {cites_html}", unsafe_allow_html=True)

            st.markdown("<hr style='margin: 8px 0; border: 0; border-top: 1px solid #1E293B;'>", unsafe_allow_html=True)

            # Quick Action Buttons
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button("🎯 Open in Results", key=f"hist_open_{inv_id}", type="primary", use_container_width=True):
                    st.session_state["current_investigation_id"] = inv_id
                    st.session_state["nav_page"] = "results"
                    st.rerun()
            with btn_col2:
                if st.button("💬 Ask in Assistant", key=f"hist_chat_{inv_id}", type="secondary", use_container_width=True):
                    st.session_state["current_investigation_id"] = inv_id
                    st.session_state["nav_page"] = "assistant"
                    st.rerun()
            with btn_col3:
                # Markdown report export
                report_md = f"""# FaultSense Diagnostic Report: {inv_id}
Elevator: {elv_id} | Subsystem: {sub} | Code: {rec.get('fault_code')}
Date: {ts} UTC | Verification: {badge_text} | Confidence: {conf}%

Root Cause Hypothesis:
{rec.get('root_cause_hypothesis', 'N/A')}

Corrective Actions:
{rec.get('recommended_actions', 'N/A')}

Evidence Cases: {', '.join(matched_cases) if matched_cases else 'None'}
"""
                st.download_button(
                    label="📄 Export Report (.md)",
                    data=report_md,
                    file_name=f"{inv_id}_report.md",
                    mime="text/markdown",
                    key=f"hist_dl_{inv_id}",
                    use_container_width=True,
                )
