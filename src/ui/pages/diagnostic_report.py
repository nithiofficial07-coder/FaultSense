"""Dedicated Diagnostic Report Page with PDF Generation, Download, and Technician Review.

Implements Step 4 of the FaultSense engineering workflow:
Submit Problem -> Analyze Evidence -> Generate PDF -> Download Report
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import streamlit as st

from src.diagnosis.diagnostic_enricher import DiagnosticEnricher
from src.knowledge_base.manager import KnowledgeBaseManager
from src.storage.repository import InvestigationRepository
from src.ui.components.sidebar import navigate_to
from src.utils.report_generator import DiagnosticReportGenerator


def render_diagnostic_report_page() -> None:
    """Renders the dedicated Diagnostic Report & Technician Field Sign-Off page."""
    # 1. Workflow Progress Stepper Banner
    st.markdown(
        """
        <div style="background: linear-gradient(90deg, #0A1120 0%, #131F37 100%); border: 1px solid #1E293B; border-radius: 10px; padding: 14px 18px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="background: rgba(16, 185, 129, 0.15); color: #10B981; font-weight: 700; font-size: 0.75rem; padding: 3px 8px; border-radius: 12px; border: 1px solid rgba(16, 185, 129, 0.3);">STEP 1</span>
                    <span style="color: #94A3B8; font-size: 0.82rem; font-weight: 600;">Submit Problem</span>
                </div>
                <div style="color: #475569; font-size: 0.8rem;">➔</div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="background: rgba(16, 185, 129, 0.15); color: #10B981; font-weight: 700; font-size: 0.75rem; padding: 3px 8px; border-radius: 12px; border: 1px solid rgba(16, 185, 129, 0.3);">STEP 2</span>
                    <span style="color: #94A3B8; font-size: 0.82rem; font-weight: 600;">Analyze Evidence</span>
                </div>
                <div style="color: #475569; font-size: 0.8rem;">➔</div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="background: rgba(16, 185, 129, 0.15); color: #10B981; font-weight: 700; font-size: 0.75rem; padding: 3px 8px; border-radius: 12px; border: 1px solid rgba(16, 185, 129, 0.3);">STEP 3</span>
                    <span style="color: #94A3B8; font-size: 0.82rem; font-weight: 600;">Generate PDF</span>
                </div>
                <div style="color: #06B6D4; font-size: 0.8rem;">➔</div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="background: rgba(6, 182, 212, 0.25); color: #38BDF8; font-weight: 800; font-size: 0.75rem; padding: 3px 9px; border-radius: 12px; border: 1px solid #06B6D4; box-shadow: 0 0 8px rgba(6, 182, 212, 0.4);">STEP 4 (ACTIVE)</span>
                    <span style="color: #F8FAFC; font-size: 0.88rem; font-weight: 700;">Download &amp; Technician Review</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    repo = InvestigationRepository()
    all_records = repo.list_all(limit=100)

    if not all_records:
        st.info("No diagnostic investigations recorded yet. Submit a problem to generate your first report.", icon="ℹ️")
        if st.button("🚀 Submit Elevator Problem", type="primary"):
            navigate_to("new_investigation")
        return

    # 2. Select Investigation (Current session active or pick past investigation)
    current_inv_id = st.session_state.get("current_investigation_id")
    inv_options = [r["investigation_id"] for r in all_records]

    default_idx = 0
    if current_inv_id and current_inv_id in inv_options:
        default_idx = inv_options.index(current_inv_id)

    def _format_inv(id_val: str) -> str:
        rec = next((r for r in all_records if r["investigation_id"] == id_val), None)
        if not rec:
            return id_val
        elv = rec.get("elevator_id", "Unknown")
        sub = str(rec.get("subsystem", "")).replace("_", " ").title()
        ts = rec.get("created_at", "")[:16].replace("T", " ")
        return f"{id_val} — Unit {elv} ({sub}) [{ts}]"

    col_sel, col_quick = st.columns([3, 1])
    with col_sel:
        selected_id = st.selectbox(
            "Select Diagnostic Investigation Session",
            options=inv_options,
            index=default_idx,
            format_func=_format_inv,
            key="diag_rep_select",
        )
    with col_quick:
        st.write("")
        st.write("")
        if st.button("➕ New Investigation", use_container_width=True):
            navigate_to("new_investigation")

    if selected_id != current_inv_id:
        st.session_state["current_investigation_id"] = selected_id

    # Load active investigation data
    inv_data = repo.get(selected_id)
    if not inv_data:
        st.error(f"Investigation session {selected_id} could not be retrieved.")
        return

    kb_manager = KnowledgeBaseManager()
    dossier = DiagnosticEnricher.enrich_investigation(inv_data, kb_manager=kb_manager)

    # 3. Investigation Summary Card & PDF Status Badge
    ev_status = dossier.evidence_based_status
    if "Verified Against" in ev_status:
        badge_color = "#34D399"
    elif "Requires Technician" in ev_status:
        badge_color = "#38BDF8"
    elif "Hypothesis" in ev_status:
        badge_color = "#F59E0B"
    else:
        badge_color = "#94A3B8"

    st.markdown(
        f"""
        <div style="background: #131F37; border: 1px solid #1E293B; border-radius: 10px; padding: 16px 20px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; margin-bottom: 12px;">
                <div>
                    <div style="font-size: 0.72rem; color: #64748B; text-transform: uppercase; font-weight: 700; letter-spacing: 0.8px;">Diagnostic Report Summary</div>
                    <div style="font-size: 1.25rem; font-weight: 800; color: #F8FAFC; margin-top: 2px;">{dossier.investigation_id}</div>
                </div>
                <div style="text-align: right;">
                    <span style="background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid rgba(16, 185, 129, 0.4); padding: 4px 10px; border-radius: 6px; font-size: 0.78rem; font-weight: 700;">
                        ● PDF REPORT GENERATED &amp; READY
                    </span>
                    <div style="font-size: 0.72rem; color: #64748B; margin-top: 4px;">Standard: ASME A17.1 / EN 81-20</div>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 12px; padding: 10px 14px; background: #0A1120; border-radius: 8px; border: 1px solid #1E293B;">
                <div><span style="color: #64748B; font-size: 0.75rem;">Elevator Unit:</span><br/><b style="color: #F8FAFC;">{dossier.elevator_id}</b></div>
                <div><span style="color: #64748B; font-size: 0.75rem;">OEM / Model:</span><br/><b style="color: #F8FAFC;">{dossier.manufacturer} {dossier.equipment_model}</b></div>
                <div><span style="color: #64748B; font-size: 0.75rem;">Affected Subsystem:</span><br/><b style="color: #38BDF8;">{dossier.subsystem.replace('_', ' ').title()}</b></div>
                <div><span style="color: #64748B; font-size: 0.75rem;">OEM DTC Code:</span><br/><code style="color: #F59E0B;">{dossier.fault_code or 'None'}</code></div>
                <div><span style="color: #64748B; font-size: 0.75rem;">Operating Severity:</span><br/><b style="color: #F8FAFC;">{dossier.severity}</b></div>
            </div>
            <div style="margin-top: 10px;">
                <span style="color: #64748B; font-size: 0.75rem; text-transform: uppercase; font-weight: 700;">AI Evidence-Based Status:</span>
                <span style="color: {badge_color}; font-weight: 700; margin-left: 6px;">● {ev_status}</span>
                <p style="margin: 6px 0 0 0; color: #E2E8F0; font-size: 0.88rem; line-height: 1.4;">
                    <b>Synthesized Primary Root Cause</b>: {dossier.primary_root_cause}
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 4. Prominent Download Action Section
    st.subheader("📥 Download Publication-Grade Technical Reports", divider="gray")
    st.markdown(
        "Download the independent 14-section engineering dossier containing all empirical evidence, required instrumentation, "
        "PPE, step-by-step manual troubleshooting checklist, and ASME A17.1 return-to-service acceptance criteria."
    )

    pdf_col, json_col, audit_col = st.columns([1.8, 1.2, 1.0])

    try:
        pdf_bytes = DiagnosticReportGenerator.generate_pdf(inv_data, kb_manager=kb_manager)
        pdf_filename = f"FaultSense_Report_{dossier.investigation_id}.pdf"
        with pdf_col:
            st.download_button(
                label="📄 Download Complete Diagnostic Report (PDF)",
                data=pdf_bytes,
                file_name=pdf_filename,
                mime="application/pdf",
                type="primary",
                key=f"rep_page_pdf_{dossier.investigation_id}",
                use_container_width=True,
            )
    except Exception as exc:
        with pdf_col:
            st.error(f"Error generating PDF report: {exc}")

    try:
        json_str = DiagnosticReportGenerator.generate_json(inv_data, kb_manager=kb_manager)
        json_filename = f"FaultSense_Data_{dossier.investigation_id}.json"
        with json_col:
            st.download_button(
                label="📦 Export Structured JSON Data",
                data=json_str,
                file_name=json_filename,
                mime="application/json",
                type="secondary",
                key=f"rep_page_json_{dossier.investigation_id}",
                use_container_width=True,
            )
    except Exception as exc:
        with json_col:
            st.caption(f"JSON export unavailable: {exc}")

    with audit_col:
        if st.button("🎯 Open in Results", use_container_width=True):
            navigate_to("results", dossier.investigation_id)

    st.markdown("<hr style='border: 0; border-top: 1px solid #1E293B; margin: 24px 0 20px 0;'>", unsafe_allow_html=True)

    # 5. Technician Review and Physical Field Verification Section
    st.subheader("🛠️ Technician Review & Physical Verification Sign-Off", divider="gray")
    st.info(
        "**Advisory Decision-Support Boundary**: FaultSense does not certify or clear an elevator. "
        "A physical elevator fault cannot be marked as resolved merely because the AI diagnostic analysis completed. "
        "Certified technicians must verify physical conditions on-site and record the outcome separately below.",
        icon="🛡️"
    )

    # Load existing technician review if previously saved
    existing_review = inv_data.get("technician_review") or {}
    prev_notes = inv_data.get("technician_notes") or ""
    prev_tech_name = existing_review.get("technician_name", "")
    prev_cert = existing_review.get("certification_number", "")
    prev_outcome = existing_review.get("verification_outcome", "Pending On-Site Inspection")
    prev_status = existing_review.get("physical_resolution_status", "Awaiting Physical Inspection")
    prev_reviewed_at = existing_review.get("reviewed_at")

    if prev_reviewed_at:
        st.success(
            f"✅ **Technician Review Recorded on {prev_reviewed_at[:19].replace('T', ' ')} UTC** by "
            f"**{prev_tech_name or 'Certified Mechanic'}** (Cert/License: `{prev_cert or 'N/A'}`) — "
            f"Outcome: **{prev_outcome}**"
        )

    with st.form(key=f"technician_review_form_{dossier.investigation_id}"):
        st.markdown("#### 1. On-Site Physical Verification Checklist")
        st.caption("Confirm each item per ASME A17.1 / CSA B44 Lockout/Tagout and inspection procedures:")

        c_chk1, c_chk2 = st.columns(2)
        with c_chk1:
            chk_loto = st.checkbox(
                "Mainline disconnect locked out (LOTO) & zero energy verified with calibrated multimeter",
                value=existing_review.get("chk_loto", False),
            )
            chk_mech = st.checkbox(
                "Subsystem mechanical clearances & air gaps measured within OEM manufacturer tolerances",
                value=existing_review.get("chk_mech", False),
            )
            chk_elec = st.checkbox(
                "Power supply rails, contacts, and safety circuit string continuity tested (0.0V drop)",
                value=existing_review.get("chk_elec", False),
            )

        with c_chk2:
            chk_align = st.checkbox(
                "Sensor alignment, optical light curtain path, or tape reader plumbness calibrated",
                value=existing_review.get("chk_align", False),
            )
            chk_test = st.checkbox(
                "Dynamic test runs executed under technician inspection control before passenger release",
                value=existing_review.get("chk_test", False),
            )
            chk_house = st.checkbox(
                "Car top, sill grooves, pit, and machine room cleared of all tools, debris, and rags",
                value=existing_review.get("chk_house", False),
            )

        st.markdown("#### 2. Technician Credentials & Findings")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            tech_name = st.text_input(
                "Lead Certified Technician Name",
                value=prev_tech_name,
                placeholder="e.g. John Doe, QEI / CET",
            )
        with col_t2:
            cert_num = st.text_input(
                "License / Certification Number",
                value=prev_cert,
                placeholder="e.g. QEI-48201 / Elevator License #",
            )

        col_o1, col_o2 = st.columns(2)
        with col_o1:
            outcome_options = [
                "Pending On-Site Inspection",
                "Confirmed AI Root Cause Correct — Fault Resolved",
                "Alternative Cause Identified & Corrected",
                "Fault Not Replicated — Monitored Under Observation",
                "Escalated to OEM Specialist / Engineering",
            ]
            outcome_idx = outcome_options.index(prev_outcome) if prev_outcome in outcome_options else 0
            verification_outcome = st.selectbox(
                "Physical Verification Outcome",
                options=outcome_options,
                index=outcome_idx,
            )

        with col_o2:
            status_options = [
                "Awaiting Physical Inspection",
                "Physically Resolved & Tested per ASME A17.1",
                "Open — Pending Parts or Further Action",
                "Inconclusive / Escalated",
            ]
            status_idx = status_options.index(prev_status) if prev_status in status_options else 0
            physical_status = st.selectbox(
                "Physical Equipment Resolution Status",
                options=status_options,
                index=status_idx,
            )

        technician_notes = st.text_area(
            "Technician Jobsite Field Notes & Measurement Findings",
            value=prev_notes,
            height=110,
            placeholder="Record exact multimeter voltage drops, feeler gauge gaps, cleaning actions taken, and return-to-service observations...",
        )

        submit_review = st.form_submit_button(
            "💾 Save Technician Review to Persistent Storage",
            type="primary",
            use_container_width=True,
        )

        if submit_review:
            review_payload = {
                "technician_name": tech_name.strip(),
                "certification_number": cert_num.strip(),
                "verification_outcome": verification_outcome,
                "physical_resolution_status": physical_status,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "chk_loto": chk_loto,
                "chk_mech": chk_mech,
                "chk_elec": chk_elec,
                "chk_align": chk_align,
                "chk_test": chk_test,
                "chk_house": chk_house,
            }
            # Record status in database without overriding AI diagnostic status blindly
            db_status = "completed" if "Physically Resolved" in physical_status else "open"
            repo.update_technician_review(
                investigation_id=dossier.investigation_id,
                technician_notes=technician_notes.strip(),
                review_data=review_payload,
                status=db_status,
            )
            st.success(
                f"✅ Technician review successfully saved to persistent database for {dossier.investigation_id}! "
                f"Any newly downloaded PDF report will now incorporate these credentials and findings."
            )
            st.rerun()


__all__ = ["render_diagnostic_report_page"]
