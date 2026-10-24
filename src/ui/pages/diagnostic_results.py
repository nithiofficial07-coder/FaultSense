"""Diagnostic Results page displaying comprehensive root-cause analysis, verification audit, and evidence."""

import json
import streamlit as st

from src.storage.repository import InvestigationRepository


def render_diagnostic_results_page() -> None:
    """Renders the comprehensive diagnostic report, verification audit, and export tools."""
    st.markdown("## 🎯 Diagnostic Investigation Results")
    st.markdown(
        "Inspect evidence-grounded root-cause syntheses, verified historical citations, and step-by-step corrective procedures."
    )

    repo = InvestigationRepository()
    all_invs = repo.list_all(limit=50)

    if not all_invs:
        st.info("No investigations recorded yet. Please run a diagnosis from **New Investigation** first.", icon="ℹ️")
        if st.button("🚀 Go to New Investigation", type="primary"):
            st.session_state["nav_page"] = "new_investigation"
            st.rerun()
        return

    # Select investigation
    inv_ids = [inv["investigation_id"] for inv in all_invs]
    curr_id = st.session_state.get("current_investigation_id")
    default_idx = inv_ids.index(curr_id) if curr_id in inv_ids else 0

    sel_col1, sel_col2 = st.columns([3, 1])
    with sel_col1:
        selected_inv_id = st.selectbox(
            "Select Investigation Session",
            options=inv_ids,
            index=default_idx,
            format_func=lambda x: f"{x} — Elevator {next((i['elevator_id'] for i in all_invs if i['investigation_id'] == x), '')} ({next((i['created_at'][:16].replace('T', ' ') for i in all_invs if i['investigation_id'] == x), '')})",
        )
    with sel_col2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("💬 Ask in Assistant", type="secondary", use_container_width=True):
            st.session_state["current_investigation_id"] = selected_inv_id
            st.session_state["nav_page"] = "assistant"
            st.rerun()

    # Load active investigation data
    inv_data = repo.get(selected_inv_id)
    if not inv_data:
        st.error(f"Investigation {selected_inv_id} not found in database.")
        return

    # Metadata Header Card
    elv_id = inv_data.get("elevator_id", "UNKNOWN")
    subsystem = str(inv_data.get("subsystem", "")).replace("_", " ").title()
    fault_code = inv_data.get("fault_code") or "N/A"
    building = inv_data.get("building_id") or "Unspecified Facility"
    ts = inv_data.get("created_at", "")[:19].replace("T", " ")
    conf_pct = int(float(inv_data.get("confidence_score", 0.0)) * 100)
    status = inv_data.get("status", "open")

    st.markdown(
        f"""
        <div style="background-color: #131F37; border: 1px solid #1E293B; border-left: 4px solid #06B6D4;
                    border-radius: 8px; padding: 16px 20px; margin: 12px 0 18px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <span style="font-size: 0.8rem; font-weight: 700; color: #06B6D4; text-transform: uppercase;">
                        Investigation Report
                    </span>
                    <h3 style="margin: 4px 0; color: #F8FAFC; font-size: 1.4rem;">{selected_inv_id}</h3>
                    <div style="color: #94A3B8; font-size: 0.85rem;">
                        Elevator Unit: <b style="color: #F1F5F9;">{elv_id}</b> | Subsystem: <b style="color: #F1F5F9;">{subsystem}</b> | Fault Code: <code style="color: #38BDF8;">{fault_code}</code>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 0.8rem; color: #64748B;">Recorded at {ts} UTC</div>
                    <div style="font-size: 0.85rem; color: #94A3B8; margin-top: 2px;">Building: <b>{building}</b></div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Verification and Confidence Metrics Row
    verif_rec = inv_data.get("verification_record") or {}
    final_verdict = verif_rec.get("final_verdict", "sufficient" if status == "completed" else "inconclusive")
    retries = inv_data.get("retry_count", 0)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Advisory Confidence", f"{conf_pct}%", help="Heuristic evidence affinity score (NOT calibrated probability)")
    with m2:
        is_verified = (final_verdict == "sufficient" or status == "completed")
        v_label = "✅ Grounded" if is_verified else "⚠️ Inconclusive"
        st.metric("Verification Verdict", v_label, delta=f"Verdict: {final_verdict.upper()}")
    with m3:
        st.metric("Refinement Retries", f"{retries} / {verif_rec.get('max_retries', 2)}", help="Number of query expansions and re-retrievals")
    with m4:
        st.metric("Evidence Cases", str(len(inv_data.get("matched_case_ids", []))), "Traceable historical records")

    # Inconclusive / Thin Evidence Warning
    if not is_verified or status == "inconclusive":
        st.warning(
            "⚠️ **INCONCLUSIVE DIAGNOSTIC ADVISORY**: This fault scenario did not achieve sufficient grounding "
            "against the current knowledge base, or contradictory physical evidence was detected. "
            "The recommendations below are heuristic suggestions only; certified technicians must execute "
            "physical multimeter isolation and safety circuit verification before replacing components.",
            icon="⚠️",
        )

    # Primary Root Cause Synthesis
    rc_text = inv_data.get("root_cause_hypothesis", "No root cause hypothesis recorded.")
    st.markdown(
        f"""
        <div style="background-color: #0F172A; border: 1px solid #1E293B; border-left: 4px solid #38BDF8;
                    padding: 16px 20px; border-radius: 8px; margin: 16px 0;">
            <div style="font-size: 0.75rem; font-weight: 700; color: #38BDF8; text-transform: uppercase; letter-spacing: 0.5px;">
                Synthesized Root-Cause Hypothesis
            </div>
            <div style="font-size: 1.1rem; color: #F8FAFC; margin-top: 8px; font-weight: 600; line-height: 1.4;">
                {rc_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Detailed Diagnostic Report Sections if available
    diag_rep = inv_data.get("diagnostic_report") or {}

    # 1. Ranked Probable Causes
    candidates = diag_rep.get("candidate_causes", [])
    if candidates:
        st.markdown("### 🔍 Ranked Probable Root Causes")
        for c in candidates:
            rank = c.get("rank", 1)
            title = c.get("hypothesis_title", "Hypothesis")
            band = c.get("probability_band", "possible").lower()
            band_badge = {"likely": "🔴 Likely", "possible": "🟡 Possible", "unlikely": "⚪ Unlikely"}.get(band, "Possible")
            cites = ", ".join(f"`{cid}`" for cid in c.get("supporting_case_ids", [])) or "None cited"

            with st.expander(f"**#{rank}. {title}** ({band_badge})", expanded=(rank == 1)):
                st.markdown(f"**Technical Explanation**:\n{c.get('explanation')}")
                st.markdown(f"**Supporting Case Citations**: {cites}")

                # Next diagnostic checks
                checks = c.get("recommended_checks", [])
                if checks:
                    st.markdown("**Recommended Next Diagnostic Checks**:")
                    for chk in checks:
                        st.markdown(f"- 🔧 {chk}")

                # Documented corrective actions
                actions = c.get("documented_corrective_actions", [])
                if actions:
                    st.markdown("**Documented Corrective Actions (from OEM sources)**:")
                    for act in actions:
                        st.markdown(f"- ✅ {act}")

                # Citation warnings
                cw = c.get("citation_warnings", [])
                if cw:
                    for w in cw:
                        st.caption(f"⚠️ {w}")

    else:
        # Fallback display of recommended actions
        st.markdown("### 🛠️ Recommended Corrective Actions")
        actions_str = inv_data.get("recommended_actions", "None documented.")
        st.markdown(actions_str)

    # 2. Safety Advisories
    safeties = diag_rep.get("safety_advisories", [])
    if safeties:
        st.markdown("### 🚨 Mandatory Technician Safety Advisories")
        for s in safeties:
            st.error(f"**SAFETY REQUIREMENT**: {s}", icon="⚠️")

    # 3. Uncertainty & Missing Information
    uncertainties = diag_rep.get("uncertainty_and_missing_info", [])
    if uncertainties:
        with st.expander("❓ Uncertainty & Missing Contextual Information"):
            for u in uncertainties:
                st.markdown(f"- {u}")

    # 4. Agentic Verification Loop Audit Trail
    if verif_rec and verif_rec.get("steps"):
        with st.expander(f"🛡️ Agentic Self-Verification Audit Trail (Status: {verif_rec.get('final_status', 'N/A')})", expanded=False):
            st.markdown(
                f"**Verification Status**: `{verif_rec.get('final_status')}` | "
                f"**Verdict**: `{verif_rec.get('final_verdict', '').upper()}` | "
                f"**Total Retries**: `{verif_rec.get('total_retries')}` / `{verif_rec.get('max_retries')}`"
            )
            st.markdown("##### Iteration Steps:")
            for step in verif_rec.get("steps", []):
                st.markdown(
                    f"- **Step #{step.get('step_number')}** — Action: `{step.get('action_taken')}` | Verdict: `{step.get('verdict')}`\n"
                    f"  - *Retrieved Cases*: `{', '.join(step.get('retrieved_case_ids', [])) or 'None'}`\n"
                    f"  - *Supported Claims*: `{step.get('supported_claims', 0)}` | *Unsupported*: `{step.get('unsupported_claims', 0)}` | *Contradicted*: `{step.get('contradicted_claims', 0)}`\n"
                    f"  - *Reasons / Notes*: {'; '.join(step.get('reasons', []))}"
                )

    # 5. Supporting Historical Case Citations
    matched_ids = inv_data.get("matched_case_ids", [])
    if matched_ids:
        st.markdown("### 📚 Historical Case Citations & Provenance")
        from src.knowledge_base.manager import KnowledgeBaseManager
        kb = KnowledgeBaseManager()

        for cid in matched_ids:
            case = kb.repo.get(cid)
            if case:
                prov_badge = "⚡ Synthetic Benchmark" if case.is_synthetic else "✓ Verified Field Record"
                prov_color = "#38BDF8" if case.is_synthetic else "#34D399"
                with st.expander(f"**{case.case_id}** — {case.source_title} ({prov_badge})"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**Subsystem**: `{case.subsystem}` | **Fault Code**: `{case.fault_code}`")
                        st.markdown(f"**Source Document**: {case.source_title} *(Ref: `{case.source_reference}`)*")
                    with c2:
                        st.markdown(f"**Verification**: `{case.verification_status}`")
                        st.markdown(f"<span style='color: {prov_color}; font-weight: 600;'>{prov_badge}</span>", unsafe_allow_html=True)

                    st.markdown(f"**Confirmed Root Cause**: {case.confirmed_root_cause}")
                    st.markdown(f"**Corrective Action Taken**: {case.corrective_action}")
                    if case.symptoms:
                        st.markdown(f"**Historical Symptoms**: {', '.join(case.symptoms)}")

    # 6. Report Export Tools
    st.markdown("---")
    st.markdown("### 📥 Export Diagnostic Report")

    # Generate Markdown export
    md_content = f"""# FaultSense Diagnostic Investigation Report
**Investigation ID**: {selected_inv_id}  
**Date**: {ts} UTC  
**Elevator Unit**: {elv_id}  
**Building / Site**: {building}  
**Subsystem**: {subsystem}  
**Fault Code**: {fault_code}  
**Verification Verdict**: {final_verdict.upper()} (Retries: {retries})  
**Advisory Confidence Score**: {conf_pct}%  

---

## 1. Primary Root-Cause Hypothesis
{rc_text}

## 2. Documented Corrective Actions
{inv_data.get('recommended_actions', 'None')}

## 3. Reported Symptoms
{chr(10).join(f"- {s}" for s in inv_data.get('symptoms', []))}

## 4. Recorded Telemetry
```json
{json.dumps(inv_data.get('telemetry', {}), indent=2)}
```

## 5. Historical Case Evidence Citations
{chr(10).join(f"- `{cid}`" for cid in matched_ids) if matched_ids else "None"}

---
*Generated by FaultSense Elevator Decision Support System. Non-control diagnostic advisory only.*
"""

    exp_col1, exp_col2, exp_col3 = st.columns([1, 1, 2])
    with exp_col1:
        st.download_button(
            label="📄 Download Markdown (.md)",
            data=md_content,
            file_name=f"{selected_inv_id}_diagnostic_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with exp_col2:
        st.download_button(
            label="📦 Download Full JSON (.json)",
            data=json.dumps(inv_data, indent=2),
            file_name=f"{selected_inv_id}_full_data.json",
            mime="application/json",
            use_container_width=True,
        )
