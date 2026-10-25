"""Diagnostic Results page displaying comprehensive root-cause analysis, verification audit, and evidence in enterprise light theme."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from src.diagnosis.diagnostic_enricher import DiagnosticDossier, DiagnosticEnricher
from src.knowledge_base.manager import KnowledgeBaseManager
from src.storage.repository import InvestigationRepository
from src.ui.components.sidebar import navigate_to
from src.utils.report_generator import DiagnosticReportGenerator


def render_diagnostic_results_page() -> None:
    """Renders the comprehensive diagnostic report, verification audit, and export tools."""
    repo = InvestigationRepository()
    all_invs = repo.list_all(limit=100)

    if not all_invs:
        st.info("No investigations recorded yet. Please run an investigation from **New Investigation** first.")
        if st.button("Go to New Investigation", icon=":material/search:", type="primary"):
            navigate_to("new_investigation")
        return

    # Select investigation
    inv_ids = [inv["investigation_id"] for inv in all_invs]
    curr_id = st.session_state.get("current_investigation_id")
    default_idx = inv_ids.index(curr_id) if curr_id in inv_ids else 0

    sel_col1, sel_col2, sel_col3 = st.columns([3.2, 1.2, 1.2])
    with sel_col1:
        selected_inv_id = st.selectbox(
            "Select Investigation Session",
            options=inv_ids,
            index=default_idx,
            format_func=lambda x: f"{x} — Elevator {next((i['elevator_id'] for i in all_invs if i['investigation_id'] == x), '')} ({next((i['created_at'][:16].replace('T', ' ') for i in all_invs if i['investigation_id'] == x), '')})",
            key="results_inv_selector",
        )
        st.session_state["current_investigation_id"] = selected_inv_id

    with sel_col2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("Ask in Assistant", icon=":material/chat:", type="secondary", use_container_width=True, key="res_btn_chat"):
            navigate_to("assistant", selected_inv_id)

    with sel_col3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("New Investigation", icon=":material/search:", type="secondary", use_container_width=True, key="res_btn_new"):
            navigate_to("new_investigation")

    # Load active investigation data
    inv_data = repo.get(selected_inv_id)
    if not inv_data:
        st.error(f"Investigation {selected_inv_id} not found in database.")
        return

    kb_manager = KnowledgeBaseManager()
    dossier: DiagnosticDossier = DiagnosticEnricher.enrich_investigation(inv_data, kb_manager=kb_manager)

    # Metadata Overview Banner in Light Theme
    ts_str = inv_data.get("created_at", "")[:19].replace("T", " ")
    status_text = dossier.evidence_based_status.upper()
    if "SUPPORTED" in status_text or "VERIFIED" in status_text:
        verif_bg = "#EFF7F2"
        verif_fg = "#3F7D62"
        verif_border = "#C6E2D3"
    elif "CONFLICTING" in status_text or "FAILED" in status_text:
        verif_bg = "#FDF2F2"
        verif_fg = "#B84C4C"
        verif_border = "#ECC4C4"
    elif "INSUFFICIENT" in status_text:
        verif_bg = "#F8FAFC"
        verif_fg = "#68778D"
        verif_border = "#E2E8F0"
    else:
        verif_bg = "#FDF8EE"
        verif_fg = "#A8752B"
        verif_border = "#EED8B4"

    st.markdown(
        f"""
        <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid #4169A8;
                    border-radius: 10px; padding: 16px 20px; margin: 10px 0 14px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <div>
                    <span style="font-size: 0.72rem; font-weight: 700; color: #4169A8; text-transform: uppercase; letter-spacing: 0.8px;">
                        INVESTIGATION DOSSIER &amp; TECHNICAL AUDIT
                    </span>
                    <h3 style="margin: 2px 0; color: #243247; font-size: 1.35rem;">{selected_inv_id}</h3>
                    <div style="color: #68778D; font-size: 0.85rem;">
                        Unit: <b style="color: #243247;">{dossier.elevator_id}</b> |
                        OEM / Model: <b style="color: #243247;">{dossier.manufacturer} ({dossier.equipment_model})</b> |
                        Subsystem: <b style="color: #243247;">{dossier.subsystem.replace('_', ' ').title()}</b> |
                        DTC: <code style="color: #4169A8; background: #EAF1FA; border: 1px solid #CADDF5; padding: 1px 4px; border-radius: 4px;">{dossier.fault_code or 'None'}</code> |
                        Severity: <b style="color: #243247;">{dossier.severity}</b>
                    </div>
                </div>
                <div style="text-align: right;">
                    <span style="background-color: {verif_bg}; color: {verif_fg};
                                 border: 1px solid {verif_border}; padding: 4px 10px; border-radius: 6px;
                                 font-size: 0.78rem; font-weight: 700; letter-spacing: 0.5px;">
                        ● {status_text}
                    </span>
                    <div style="font-size: 0.75rem; color: #68778D; margin-top: 5px;">Recorded: {ts_str} UTC</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Top-Level Prominent Report Download Bar
    top_c1, top_c2, top_c3, top_c4 = st.columns([1.5, 1.1, 1.2, 1.2])
    with top_c1:
        try:
            top_pdf_bytes = DiagnosticReportGenerator.generate_pdf(inv_data, kb_manager=kb_manager)
            st.download_button(
                label="Download Report (PDF)",
                icon=":material/description:",
                data=top_pdf_bytes,
                file_name=f"FaultSense_Report_{selected_inv_id}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
                key=f"top_dl_pdf_{selected_inv_id}",
            )
        except Exception as exc:
            st.error(f"Error compiling PDF: {exc}")

    with top_c2:
        try:
            top_json_str = DiagnosticReportGenerator.generate_json(inv_data, kb_manager=kb_manager)
            st.download_button(
                label="Export JSON",
                icon=":material/download:",
                data=top_json_str,
                file_name=f"FaultSense_Data_{selected_inv_id}.json",
                mime="application/json",
                type="secondary",
                use_container_width=True,
                key=f"top_dl_json_{selected_inv_id}",
            )
        except Exception:
            pass

    with top_c3:
        if st.button("Report & Review Page", icon=":material/description:", key=f"top_btn_report_{selected_inv_id}", type="secondary", use_container_width=True):
            navigate_to("report", selected_inv_id)

    with top_c4:
        st.caption(f"Status: **{dossier.evidence_based_status}**\nAdvisory Match: **{int(dossier.confidence_score * 100)}%**")

    st.markdown("<hr style='margin: 8px 0 14px 0; border: 0; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)

    # 8-Tab Detailed Results Interface
    tab_summary, tab_rca, tab_evidence, tab_telemetry, tab_tools, tab_steps, tab_safety, tab_report = st.tabs([
        "Executive Summary",
        "Root-Cause Analysis",
        "Evidence & Precedents",
        "Telemetry Analysis",
        "Required Tools",
        "Troubleshooting Manual",
        "Safety & Verification",
        "Downloadable Report",
    ])

    # =========================================================================
    # Tab 1: Executive Summary
    # =========================================================================
    with tab_summary:
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric(
                "Advisory Confidence",
                f"{int(dossier.confidence_score * 100)}%",
                help="Empirical evidence support score based on measurable empirical factors (NOT a calibrated statistical probability)",
            )
        with m2:
            st.metric("Diagnostic Status", dossier.evidence_based_status)
        with m3:
            retry_count = int(inv_data.get("retry_count", 0))
            if retry_count == 0 and dossier.is_verified:
                retry_str = "0 (Passed 1st Step)"
            elif retry_count > 0:
                retry_str = f"{retry_count} retries ({retry_count + 1} steps)"
            else:
                retry_str = "0 retries (Unverified)"
            st.metric("Verification Retries", retry_str)
        with m4:
            st.metric("Matched Evidence Cases", str(len(dossier.supporting_evidence)))

        bd = getattr(dossier, "confidence_breakdown", None) or inv_data.get("confidence_breakdown") or {}
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

        if not dossier.is_verified:
            st.warning(
                "**INCONCLUSIVE ADVISORY**: This fault scenario did not achieve conclusive evidence grounding, "
                "or physical telemetry readings contradict single-point failure modes. "
                "The findings below are preliminary guidelines. Certified technicians must verify physical safety "
                "interlocks and perform multimeter isolation prior to replacing components."
            )

        # Primary Hypothesis
        st.markdown(
            f"""
            <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid #4169A8;
                        padding: 16px 20px; border-radius: 10px; margin: 12px 0 16px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="font-size: 0.75rem; font-weight: 700; color: #4169A8; text-transform: uppercase; letter-spacing: 0.5px;">
                    Synthesized Primary Root-Cause Hypothesis
                </div>
                <div style="font-size: 1.15rem; color: #243247; margin-top: 6px; font-weight: 700; line-height: 1.4;">
                    {dossier.primary_root_cause}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Recommended immediate action
        st.markdown(
            f"""
            <div style="background: #EAF1FA; border: 1px solid #CADDF5;
                        padding: 14px 18px; border-radius: 10px; margin-bottom: 14px;">
                <div style="font-size: 0.75rem; font-weight: 700; color: #243F6C; text-transform: uppercase;">
                    Recommended Immediate Action
                </div>
                <div style="font-size: 0.95rem; color: #243247; margin-top: 4px; font-weight: 500;">
                    {dossier.recommended_next_action}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Reported Symptoms Summary
        st.markdown("##### Reported Incident Symptoms")
        for sym in dossier.symptoms:
            st.markdown(f"- {sym}")

        if inv_data.get("technician_notes"):
            st.markdown(f"**Field Notes**: {inv_data.get('technician_notes')}")

    # =========================================================================
    # Tab 2: Root-Cause Analysis
    # =========================================================================
    with tab_rca:
        st.markdown("### Ranked Probable Root Causes")
        st.caption("Hypotheses ranked by semantic similarity and multi-factor historical evidence grounding.")

        for c in dossier.ranked_causes:
            rank = c.get("rank", 1)
            title = c.get("hypothesis_title", "Candidate Cause")
            band = c.get("probability_band", "possible").upper()
            band_badge = {"LIKELY": "Likely Precedent", "POSSIBLE": "Possible Cause", "UNLIKELY": "Low Probability"}.get(band, band)
            cites = ", ".join(f"`{cid}`" for cid in c.get("supporting_case_ids", [])) or "None cited"

            with st.expander(f"**#{rank}. {title}** ({band_badge})", expanded=(rank == 1)):
                st.markdown(f"**Technical Explanation**:\n{c.get('explanation')}")
                st.markdown(f"**Supporting Case Precedents**: {cites}")

                checks = c.get("recommended_checks", [])
                if checks:
                    st.markdown("**Next Diagnostic Checks**:")
                    for chk in checks:
                        st.markdown(f"- {chk}")

                actions = c.get("documented_corrective_actions", [])
                if actions:
                    st.markdown("**Documented Corrective Actions (OEM Sources)**:")
                    for act in actions:
                        st.markdown(f"- {act}")

                warnings = c.get("citation_warnings", [])
                if warnings:
                    for w in warnings:
                        st.caption(f"Advisory: {w}")

    # =========================================================================
    # Tab 3: Evidence & Precedents
    # =========================================================================
    with tab_evidence:
        st.markdown("### Historical Maintenance Records & Precedents")
        st.caption("Traceable OEM technical advisories and verified field incident precedents cited by the retrieval engine.")

        if not dossier.supporting_evidence:
            st.info("No explicit historical cases matched above the similarity threshold for this session.")
        else:
            for ev in dossier.supporting_evidence:
                prov_badge = "Synthetic Benchmark Case" if ev.get("is_synthetic") else "Verified Field Incident"
                prov_color = "#4169A8" if ev.get("is_synthetic") else "#3F7D62"

                with st.expander(f"**{ev['case_id']}** — {ev['source_title']} ({prov_badge})"):
                    e1, e2 = st.columns(2)
                    with e1:
                        st.markdown(f"**Subsystem**: `{ev['subsystem']}` | **DTC Code**: `{ev['fault_code']}`")
                        st.markdown(f"**Source Document**: {ev['source_title']} *(Ref: `{ev['source_reference']}`)*")
                    with e2:
                        st.markdown(f"**Verification**: `{ev['verification_status']}`")
                        st.markdown(f"<span style='color: {prov_color}; font-weight: 700;'>● {prov_badge}</span>", unsafe_allow_html=True)

                    st.markdown(f"**Confirmed Root Cause**: {ev['confirmed_root_cause']}")
                    st.markdown(f"**Corrective Action Taken**: {ev['corrective_action']}")

    # =========================================================================
    # Tab 4: Telemetry Analysis
    # =========================================================================
    with tab_telemetry:
        st.markdown("### Physical Controller Telemetry Readings")
        st.caption("Quantitative sensor signals evaluated against manufacturer operating limits.")

        if not dossier.telemetry_readings:
            st.info("No physical telemetry data recorded for this session. System operated in symptom-matching mode.")
        else:
            df_tel = pd.DataFrame([
                {
                    "Sensor Parameter": t["parameter"],
                    "Reading": t["value"],
                    "Unit": t["unit"],
                    "Nominal Baseline": t["nominal_range"],
                    "Operating Condition": t["assessment"],
                }
                for t in dossier.telemetry_readings
            ])
            st.dataframe(df_tel, hide_index=True, use_container_width=True)

        st.markdown("##### Telemetry Data Quality Evaluation")
        st.info(f"**Quality Rating**: {dossier.data_quality_assessment} | **Sufficiency Level**: `{dossier.input_sufficiency}`")

    # =========================================================================
    # Tab 5: Required Tools
    # =========================================================================
    with tab_tools:
        st.markdown("### Required Diagnostic Tools, Equipment & Instruments")
        st.caption("Subsystem-specific tooling and calibrated instruments required to verify or isolate the failure mode.")

        for t in dossier.required_tools:
            st.markdown(
                f"""
                <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-left: 3px solid #4169A8;
                            border-radius: 10px; padding: 14px 18px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 1.05rem; font-weight: 700; color: #243247;">{t.name}</span>
                        <span style="font-size: 0.72rem; color: #4169A8; font-weight: 700; text-transform: uppercase;">MANDATORY INSTRUMENT</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #68778D; margin-top: 4px;"><b>Purpose</b>: {t.purpose}</div>
                    <div style="font-size: 0.85rem; color: #243247; margin-top: 4px;"><b>Why Needed for this Fault</b>: {t.why_needed}</div>
                    <div style="font-size: 0.82rem; color: #4169A8; margin-top: 4px;"><b>Inspection Protocol</b>: {t.inspection_step}</div>
                    <div style="font-size: 0.8rem; color: #B84C4C; margin-top: 4px;"><b>Safety Precaution</b>: {t.safety_precautions}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # =========================================================================
    # Tab 6: Troubleshooting Manual & Parts
    # =========================================================================
    with tab_steps:
        st.markdown("### Step-by-Step Manual Troubleshooting Procedure")
        st.caption(
            "Ordered engineering checklist adhering to ASME A17.1 / EN 81 safety protocols. "
            "Diagnostic inspections must be completed prior to performing corrective actions."
        )

        for step in dossier.troubleshooting_manual:
            is_insp = (step.step_type == "Diagnostic Inspection")
            type_bg = "#EAF1FA" if is_insp else "#EFF7F2"
            type_fg = "#4169A8" if is_insp else "#3F7D62"
            type_border = "#CADDF5" if is_insp else "#C6E2D3"

            st.markdown(
                f"""
                <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid {type_fg};
                            border-radius: 10px; padding: 14px 18px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 1.0rem; font-weight: 700; color: #243247;">
                            Step {step.step_number}: {step.title}
                        </span>
                        <span style="background-color: {type_bg}; color: {type_fg};
                                     border: 1px solid {type_border}; padding: 2px 8px; border-radius: 4px;
                                     font-size: 0.72rem; font-weight: 700; text-transform: uppercase;">
                            {step.step_type}
                        </span>
                    </div>
                    <div style="font-size: 0.84rem; color: #68778D; margin-bottom: 4px;">
                        <b>Purpose</b>: {step.purpose}
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 8px; font-size: 0.82rem;">
                        <div>
                            <div style="color: #243247;"><b>Tools Required</b>: <code style="color: #4169A8;">{step.required_tools}</code></div>
                            <div style="color: #243247; margin-top: 4px;"><b>Inspection / Measurement</b>: {step.inspection_measurement}</div>
                        </div>
                        <div>
                            <div style="color: #3F7D62;"><b>Expected Criterion</b>: {step.expected_criterion}</div>
                            <div style="color: #68778D; margin-top: 4px;"><b>Result Interpretation</b>: {step.interpretation}</div>
                            <div style="color: #4169A8; margin-top: 4px;"><b>Next Action</b>: {step.next_action}</div>
                        </div>
                    </div>
                    <div style="margin-top: 8px; padding: 6px 10px; background-color: #FDF2F2; border-left: 2px solid #B84C4C; border-radius: 4px; font-size: 0.78rem; color: #8C2F2F;">
                        <b>Safety Warning &amp; Stop Condition</b>: {step.safety_precautions}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("### Recommended Replacement Parts (Grounded in Evidence)")
        if dossier.recommended_parts:
            for p in dossier.recommended_parts:
                st.markdown(
                    f"""
                    <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-left: 3px solid #4169A8;
                                border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
                        <div style="font-weight: 700; color: #243247;">{p.part_name} <span style="font-size: 0.75rem; color: #68778D;">({p.part_type})</span></div>
                        <div style="font-size: 0.82rem; color: #68778D; margin-top: 2px;"><b>Justification</b>: {p.justification}</div>
                        <div style="font-size: 0.78rem; color: #4169A8; margin-top: 2px;"><b>Evidence Basis</b>: {p.evidence_basis}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("No immediate component replacements recommended. Evidence suggests mechanical cleaning, alignment, or circuit continuity testing will resolve the condition.")

        st.markdown("---")
        st.markdown("### Estimated Effort & Downtime")
        de = dossier.downtime_estimate
        c_i, c_s, c_t = st.columns(3)
        with c_i:
            st.metric("Inspection Time", f"{de.inspection_hours:.1f} hrs")
        with c_s:
            st.metric("Service / Repair Time", f"{de.service_hours:.1f} hrs")
        with c_t:
            st.metric("Total Estimated Downtime", f"{de.total_hours:.1f} hrs")
        st.caption(f"**Defensible Basis**: {de.defensible_basis}")

    # =========================================================================
    # Tab 7: Safety & Verification
    # =========================================================================
    with tab_safety:
        st.markdown("### Mandatory Technician Safety Precautions")
        for s in dossier.safety_precautions:
            st.error(f"**SAFETY**: {s}")

        st.markdown("### Escalation Requirements")
        for e in dossier.escalation_requirements:
            st.warning(f"**ESCALATION**: {e}")

        st.markdown("---")
        st.markdown("### Return-to-Service Verification Checklist (ASME A17.1)")
        for chk in dossier.return_to_service_checks:
            st.markdown(
                f"""
                <div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;">
                    <div style="font-weight: 700; color: #243247;">
                        Step {chk.step_number}: {chk.title} <span style="color: #4169A8; font-size: 0.78rem;">[{chk.applicable_code}]</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #68778D; margin-top: 3px;">
                        <b>Acceptance Criterion</b>: {chk.acceptance_criterion}
                    </div>
                    <div style="font-size: 0.78rem; color: #68778D; margin-top: 2px;">
                        <b>Safety Advisory</b>: {chk.safety_advisory}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Verification Loop Audit Trail if available
        verif_rec = inv_data.get("verification_record")
        if verif_rec and verif_rec.get("steps"):
            st.markdown("---")
            with st.expander("Agentic Self-Verification Loop Audit Trail", expanded=False):
                st.markdown(
                    f"**Final Status**: `{verif_rec.get('final_status')}` | "
                    f"**Final Verdict**: `{verif_rec.get('final_verdict', '').upper()}` | "
                    f"**Total Retries**: `{verif_rec.get('total_retries')}` / `{verif_rec.get('max_retries')}`"
                )
                for step in verif_rec.get("steps", []):
                    st.markdown(
                        f"- **Step #{step.get('step_number')}** — Action: `{step.get('action_taken')}` | Verdict: `{step.get('verdict')}`\n"
                        f"  - *Retrieved Cases*: `{', '.join(step.get('retrieved_case_ids', [])) or 'None'}`\n"
                        f"  - *Supported Claims*: `{step.get('supported_claims', 0)}` | *Unsupported*: `{step.get('unsupported_claims', 0)}` | *Contradicted*: `{step.get('contradicted_claims', 0)}`\n"
                        f"  - *Reasons / Query Refinements*: {'; '.join(step.get('reasons', []))}"
                    )

    # =========================================================================
    # Tab 8: Downloadable Report
    # =========================================================================
    with tab_report:
        st.markdown("### Download Diagnostic Investigation Report")
        st.markdown(
            "Download an authoritative, publication-grade PDF report or structured JSON export for record keeping, "
            "OEM warranty claims, and building management work orders."
        )

        # Generate artifacts
        try:
            pdf_bytes = DiagnosticReportGenerator.generate_pdf(inv_data, kb_manager=kb_manager)
            json_str = DiagnosticReportGenerator.generate_json(inv_data, kb_manager=kb_manager)
            has_pdf = True
        except Exception as exc:
            st.error(f"Error generating PDF report: {exc}")
            pdf_bytes = b""
            json_str = json.dumps(inv_data, indent=2)
            has_pdf = False

        c_pdf, c_json, c_md, c_page = st.columns([1.5, 1.1, 1.1, 1.3])

        with c_pdf:
            if has_pdf:
                st.download_button(
                    label="Download Report (PDF)",
                    icon=":material/description:",
                    data=pdf_bytes,
                    file_name=f"FaultSense_Report_{selected_inv_id}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True,
                    key=f"dl_pdf_{selected_inv_id}",
                )
                st.caption(f"PDF size: {len(pdf_bytes) / 1024:.1f} KB. Includes 14 formal engineering sections.")

        with c_json:
            st.download_button(
                label="Export JSON (.json)",
                icon=":material/download:",
                data=json_str,
                file_name=f"FaultSense_Data_{selected_inv_id}.json",
                mime="application/json",
                type="secondary",
                use_container_width=True,
                key=f"dl_json_{selected_inv_id}",
            )
            st.caption("Complete 18-point structured dossier.")

        with c_md:
            md_text = f"""# FaultSense Diagnostic Report: {selected_inv_id}
**Elevator Unit**: {dossier.elevator_id} | **OEM / Model**: {dossier.manufacturer} ({dossier.equipment_model}) | **Subsystem**: {dossier.subsystem} | **DTC**: {dossier.fault_code}
**Diagnostic Status**: {dossier.evidence_based_status} | **Confidence**: {int(dossier.confidence_score * 100)}%

## 1. Primary Root Cause
{dossier.primary_root_cause}

## 2. Recommended Next Action
{dossier.recommended_next_action}

## 3. Problem Description & Observed Symptoms
{dossier.problem_description}
{chr(10).join(f"- {s}" for s in dossier.symptoms)}

## 4. Telemetry Summary
{json.dumps(dossier.telemetry_readings, indent=2)}
"""
            st.download_button(
                label="Export Markdown (.md)",
                icon=":material/description:",
                data=md_text,
                file_name=f"FaultSense_Summary_{selected_inv_id}.md",
                mime="text/markdown",
                type="secondary",
                use_container_width=True,
                key=f"dl_md_{selected_inv_id}",
            )
            st.caption("Plain text summary.")

        with c_page:
            if st.button("Technician Sign-Off Page", icon=":material/edit_note:", type="secondary", use_container_width=True, key=f"tab8_btn_rep_{selected_inv_id}"):
                navigate_to("report", selected_inv_id)
            st.caption("Record field measurements & sign-off.")

        st.markdown("---")
        st.markdown("##### PDF Engineering Dossier Structure")
        st.caption("The 14 formal sections compiled into the downloaded PDF document:")
        doc_sections = [
            "1. FaultSense Report Title and Branding",
            "2. Investigation ID, Date, and Equipment Details",
            "3. Executive Summary & Diagnostic Status",
            "4. Reported Problem, Observed Symptoms, and Error Codes",
            "5. Telemetry & Data-Quality Analysis",
            "6. Suspected Root Cause and Alternative Hypotheses",
            "7. Supporting Evidence and Historical Case References",
            "8. Required Diagnostic Tools, Instruments, and PPE",
            "9. Detailed Numbered Manual Troubleshooting Procedure",
            "10. Recommended Corrective Actions Supported by Evidence",
            "11. Safety Instructions and Critical Stop Conditions",
            "12. Verification Checklist and Acceptance Criteria (with Sign-Off Block)",
            "13. Unresolved Issues, Outstanding Risks, and Recommended Next Steps",
            "14. Sources, Limitations, and Regulatory Safety Disclaimer (ASME A17.1)",
        ]
        for sec in doc_sections:
            st.markdown(f"- {sec}")
