"""Diagnostic Results page displaying comprehensive root-cause analysis, verification audit, and evidence."""

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
        st.info("No investigations recorded yet. Please run an investigation from **New Investigation** first.", icon="ℹ️")
        if st.button("🚀 Go to New Investigation", type="primary"):
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
        if st.button("💬 Ask in Assistant", type="secondary", use_container_width=True, key="res_btn_chat"):
            navigate_to("assistant", selected_inv_id)

    with sel_col3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("➕ New Investigation", type="secondary", use_container_width=True, key="res_btn_new"):
            navigate_to("new_investigation")

    # Load active investigation data
    inv_data = repo.get(selected_inv_id)
    if not inv_data:
        st.error(f"Investigation {selected_inv_id} not found in database.", icon="🚨")
        return

    kb_manager = KnowledgeBaseManager()
    dossier: DiagnosticDossier = DiagnosticEnricher.enrich_investigation(inv_data, kb_manager=kb_manager)

    # Metadata Overview Banner
    ts_str = inv_data.get("created_at", "")[:19].replace("T", " ")
    verif_badge_color = "#34D399" if dossier.is_verified else "#F59E0B"
    verif_status_text = "VERIFIED GROUNDED" if dossier.is_verified else "INCONCLUSIVE ADVISORY"

    st.markdown(
        f"""
        <div style="background-color: #131F37; border: 1px solid #1E293B; border-left: 4px solid #06B6D4;
                    border-radius: 8px; padding: 14px 18px; margin: 10px 0 16px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <div>
                    <span style="font-size: 0.72rem; font-weight: 700; color: #06B6D4; text-transform: uppercase; letter-spacing: 0.8px;">
                        INVESTIGATION DOSSIER
                    </span>
                    <h3 style="margin: 2px 0; color: #F8FAFC; font-size: 1.35rem;">{selected_inv_id}</h3>
                    <div style="color: #94A3B8; font-size: 0.85rem;">
                        Elevator Unit: <b style="color: #F1F5F9;">{dossier.elevator_id}</b> |
                        Subsystem: <b style="color: #F1F5F9;">{dossier.subsystem.replace('_', ' ').title()}</b> |
                        DTC Code: <code style="color: #38BDF8;">{dossier.fault_code or 'None'}</code> |
                        Site: <b style="color: #F1F5F9;">{dossier.building_id}</b>
                    </div>
                </div>
                <div style="text-align: right;">
                    <span style="background-color: rgba(6, 182, 212, 0.1); color: {verif_badge_color};
                                 border: 1px solid {verif_badge_color}; padding: 3px 10px; border-radius: 6px;
                                 font-size: 0.78rem; font-weight: 700; letter-spacing: 0.5px;">
                        ● {verif_status_text}
                    </span>
                    <div style="font-size: 0.75rem; color: #64748B; margin-top: 5px;">Recorded: {ts_str} UTC</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 8-Tab Detailed Results Interface
    tab_summary, tab_rca, tab_evidence, tab_telemetry, tab_tools, tab_steps, tab_safety, tab_report = st.tabs([
        "📋 Executive Summary",
        "🎯 Root-Cause Analysis",
        "📚 Evidence & Precedents",
        "📡 Telemetry Analysis",
        "🔧 Required Tools",
        "🛠️ Inspection Procedure",
        "🛡️ Safety & Verification",
        "📥 Downloadable Report",
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
                help="Evidence affinity score based on historical precedent similarity (NOT a calibrated probability)",
            )
        with m2:
            verif_delta = "Grounded against KB" if dossier.is_verified else "Retries exhausted"
            st.metric("Verification Status", dossier.verification_status, delta=verif_delta)
        with m3:
            st.metric("Input Sufficiency", dossier.input_sufficiency, help="Completeness of symptoms, fault code, and telemetry")
        with m4:
            st.metric("Evidence Cases", str(len(dossier.supporting_evidence)), "Citing OEM bulletins")

        if not dossier.is_verified:
            st.warning(
                "⚠️ **INCONCLUSIVE ADVISORY**: This fault scenario did not achieve conclusive evidence grounding, "
                "or physical telemetry readings contradict single-point failure modes. "
                "The findings below are preliminary guidelines. Certified technicians must verify physical safety "
                "interlocks and perform multimeter isolation prior to replacing components.",
                icon="⚠️",
            )

        # Primary Hypothesis
        st.markdown(
            f"""
            <div style="background-color: #0F172A; border: 1px solid #1E293B; border-left: 4px solid #38BDF8;
                        padding: 16px 20px; border-radius: 8px; margin: 12px 0 16px 0;">
                <div style="font-size: 0.75rem; font-weight: 700; color: #38BDF8; text-transform: uppercase; letter-spacing: 0.5px;">
                    Synthesized Primary Root-Cause Hypothesis
                </div>
                <div style="font-size: 1.15rem; color: #F8FAFC; margin-top: 6px; font-weight: 700; line-height: 1.4;">
                    {dossier.primary_root_cause}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Recommended immediate action
        st.markdown(
            f"""
            <div style="background: rgba(6, 182, 212, 0.08); border: 1px solid rgba(6, 182, 212, 0.25);
                        padding: 14px 18px; border-radius: 8px; margin-bottom: 14px;">
                <div style="font-size: 0.75rem; font-weight: 700; color: #06B6D4; text-transform: uppercase;">
                    Recommended Immediate Action
                </div>
                <div style="font-size: 0.95rem; color: #F1F5F9; margin-top: 4px; font-weight: 500;">
                    {dossier.recommended_next_action}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Reported Symptoms Summary
        st.markdown("##### 🔍 Reported Incident Symptoms")
        for sym in dossier.symptoms:
            st.markdown(f"- ⚠️ {sym}")

        if inv_data.get("technician_notes"):
            st.markdown(f"**Field Notes**: {inv_data.get('technician_notes')}")

    # =========================================================================
    # Tab 2: Root-Cause Analysis
    # =========================================================================
    with tab_rca:
        st.markdown("### 🎯 Ranked Probable Root Causes")
        st.caption("Hypotheses ranked by semantic similarity and multi-factor historical evidence grounding.")

        for c in dossier.ranked_causes:
            rank = c.get("rank", 1)
            title = c.get("hypothesis_title", "Candidate Cause")
            band = c.get("probability_band", "possible").upper()
            band_badge = {"LIKELY": "🔴 Likely Precedent", "POSSIBLE": "🟡 Possible Cause", "UNLIKELY": "⚪ Low Probability"}.get(band, band)
            cites = ", ".join(f"`{cid}`" for cid in c.get("supporting_case_ids", [])) or "None cited"

            with st.expander(f"**#{rank}. {title}** ({band_badge})", expanded=(rank == 1)):
                st.markdown(f"**Technical Explanation**:\n{c.get('explanation')}")
                st.markdown(f"**Supporting Case Precedents**: {cites}")

                checks = c.get("recommended_checks", [])
                if checks:
                    st.markdown("**Next Diagnostic Checks**:")
                    for chk in checks:
                        st.markdown(f"- 🔧 {chk}")

                actions = c.get("documented_corrective_actions", [])
                if actions:
                    st.markdown("**Documented Corrective Actions (OEM Sources)**:")
                    for act in actions:
                        st.markdown(f"- ✅ {act}")

                warnings = c.get("citation_warnings", [])
                if warnings:
                    for w in warnings:
                        st.caption(f"⚠️ {w}")

    # =========================================================================
    # Tab 3: Evidence & Precedents
    # =========================================================================
    with tab_evidence:
        st.markdown("### 📚 Historical Maintenance Records & Precedents")
        st.caption("Traceable OEM technical advisories and verified field incident precedents cited by the retrieval engine.")

        if not dossier.supporting_evidence:
            st.info("No explicit historical cases matched above the similarity threshold for this session.")
        else:
            for ev in dossier.supporting_evidence:
                prov_badge = "⚡ Synthetic Benchmark Case" if ev["is_synthetic"] else "✓ Verified Field Incident"
                prov_color = "#38BDF8" if ev["is_synthetic"] else "#34D399"

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
        st.markdown("### 📡 Physical Controller Telemetry Readings")
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

        st.markdown("##### 📊 Telemetry Data Quality Evaluation")
        st.info(f"**Quality Rating**: {dossier.data_quality_assessment} | **Sufficiency Level**: `{dossier.input_sufficiency}`")

    # =========================================================================
    # Tab 5: Required Tools
    # =========================================================================
    with tab_tools:
        st.markdown("### 🔧 Required Diagnostic Tools, Equipment & Instruments")
        st.caption("Subsystem-specific tooling and calibrated instruments required to verify or isolate the failure mode.")

        for t in dossier.required_tools:
            st.markdown(
                f"""
                <div style="background-color: #131F37; border: 1px solid #1E293B; border-left: 3px solid #06B6D4;
                            border-radius: 8px; padding: 14px 18px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 1.05rem; font-weight: 700; color: #F8FAFC;">{t.name}</span>
                        <span style="font-size: 0.72rem; color: #06B6D4; font-weight: 700; text-transform: uppercase;">MANDATORY INSTRUMENT</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #94A3B8; margin-top: 4px;"><b>Purpose</b>: {t.purpose}</div>
                    <div style="font-size: 0.85rem; color: #E2E8F0; margin-top: 4px;"><b>Why Needed for this Fault</b>: {t.why_needed}</div>
                    <div style="font-size: 0.82rem; color: #38BDF8; margin-top: 4px;"><b>Inspection Protocol</b>: {t.inspection_step}</div>
                    <div style="font-size: 0.8rem; color: #F87171; margin-top: 4px;">⚠️ <b>Safety Precaution</b>: {t.safety_precautions}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # =========================================================================
    # Tab 6: Inspection Procedure & Parts
    # =========================================================================
    with tab_steps:
        st.markdown("### 🛠️ Recommended Step-by-Step Inspection Procedure")

        for idx, step in enumerate(dossier.inspection_steps, 1):
            st.markdown(f"**Step {idx}**: {step}")

        st.markdown("---")
        st.markdown("### 🔩 Recommended Replacement Parts (Grounded in Evidence)")
        if dossier.recommended_parts:
            for p in dossier.recommended_parts:
                st.markdown(
                    f"""
                    <div style="background-color: #131F37; border: 1px solid #1E293B; border-left: 3px solid #38BDF8;
                                border-radius: 6px; padding: 10px 14px; margin-bottom: 8px;">
                        <div style="font-weight: 700; color: #F8FAFC;">{p.part_name} <span style="font-size: 0.75rem; color: #94A3B8;">({p.part_type})</span></div>
                        <div style="font-size: 0.82rem; color: #E2E8F0; margin-top: 2px;"><b>Justification</b>: {p.justification}</div>
                        <div style="font-size: 0.78rem; color: #06B6D4; margin-top: 2px;"><b>Evidence Basis</b>: {p.evidence_basis}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("No immediate component replacements recommended. Evidence suggests mechanical cleaning, alignment, or circuit continuity testing will resolve the condition.")

        st.markdown("---")
        st.markdown("### ⏱️ Estimated Effort & Downtime")
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
        st.markdown("### 🚨 Mandatory Technician Safety Precautions")
        for s in dossier.safety_precautions:
            st.error(f"⚠️ **SAFETY**: {s}", icon="⚠️")

        st.markdown("### 📞 Escalation Requirements")
        for e in dossier.escalation_requirements:
            st.warning(f"🚨 **ESCALATION**: {e}", icon="🚨")

        st.markdown("---")
        st.markdown("### ✅ Return-to-Service Verification Checklist (ASME A17.1)")
        for chk in dossier.return_to_service_checks:
            st.markdown(
                f"""
                <div style="background-color: #0E1726; border: 1px solid #1E293B; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px;">
                    <div style="font-weight: 700; color: #F8FAFC;">
                        Step {chk.step_number}: {chk.title} <span style="color: #06B6D4; font-size: 0.78rem;">[{chk.applicable_code}]</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #E2E8F0; margin-top: 3px;">
                        <b>Acceptance Criterion</b>: {chk.acceptance_criterion}
                    </div>
                    <div style="font-size: 0.78rem; color: #94A3B8; margin-top: 2px;">
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
            with st.expander("🛡️ Agentic Self-Verification Loop Audit Trail", expanded=False):
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
        st.markdown("### 📥 Download Diagnostic Investigation Report")
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

        c_pdf, c_json, c_md = st.columns(3)

        with c_pdf:
            if has_pdf:
                st.download_button(
                    label="📄 Download Diagnostic Report (PDF)",
                    data=pdf_bytes,
                    file_name=f"{selected_inv_id}_FaultSense_Report.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True,
                    key=f"dl_pdf_{selected_inv_id}",
                )
                st.caption(f"PDF size: {len(pdf_bytes) / 1024:.1f} KB. Includes vector branding & ASME A17.1 checklist.")

        with c_json:
            st.download_button(
                label="📦 Download Full JSON (.json)",
                data=json_str,
                file_name=f"{selected_inv_id}_diagnostic_data.json",
                mime="application/json",
                type="secondary",
                use_container_width=True,
                key=f"dl_json_{selected_inv_id}",
            )
            st.caption("Complete 18-point structured dossier with evidence citations and raw telemetry.")

        with c_md:
            md_text = f"""# FaultSense Diagnostic Report: {selected_inv_id}
**Elevator Unit**: {dossier.elevator_id} | **Subsystem**: {dossier.subsystem} | **DTC**: {dossier.fault_code}
**Verification Status**: {dossier.verification_status} | **Confidence**: {int(dossier.confidence_score * 100)}%

## 1. Primary Root Cause
{dossier.primary_root_cause}

## 2. Recommended Next Action
{dossier.recommended_next_action}

## 3. Reported Symptoms
{chr(10).join(f"- {s}" for s in dossier.symptoms)}

## 4. Telemetry Summary
{json.dumps(dossier.telemetry_readings, indent=2)}
"""
            st.download_button(
                label="📝 Download Markdown (.md)",
                data=md_text,
                file_name=f"{selected_inv_id}_report.md",
                mime="text/markdown",
                type="secondary",
                use_container_width=True,
                key=f"dl_md_{selected_inv_id}",
            )
            st.caption("Lightweight plain text Markdown summary.")

        st.markdown("---")
        st.markdown("##### 📄 PDF Document Structure Preview")
        st.caption("Sections compiled in the downloaded PDF:")
        doc_sections = [
            "1. Header Banner & Vector Branding (Report ID, Timestamp, ASME A17.1 / EN 81-20)",
            "2. Executive Summary & Verification Card (Unit, DTC, Verdict, Confidence, Sufficiency)",
            "3. Primary Root Cause Synthesis & Immediate Recommended Action",
            "4. Reported Symptoms & Physical Sensor Telemetry Table",
            "5. Ranked Probable Causes & Traceable Historical Evidence Citations Table",
            "6. Required Diagnostic Tools, Equipment & Safety Measures Table",
            "7. Step-by-Step Inspection Procedure & Component Wear Replacement Table",
            "8. Defensible Service Downtime & Effort Duration Estimate",
            "9. Mandatory Safety Precautions & Escalation Protocols",
            "10. Return-to-Service Acceptance Checklist with Technician Sign-Off Boxes",
            "11. Known Limitations, Missing Data & Regulatory Advisory Disclaimer",
            "12. Dynamic Numbered Canvas Running Footer ('Page X of Y')",
        ]
        for sec in doc_sections:
            st.markdown(f"- 📑 {sec}")
