"""Overview and system dashboard page for FaultSense with live metrics from stored data."""

import pandas as pd
import streamlit as st

from src.knowledge_base.manager import KnowledgeBaseManager
from src.retrieval.index_manager import IndexManager
from src.storage.repository import InvestigationRepository
from src.ui.components.cards import render_metric_card


def render_overview_page() -> None:
    """Renders the executive summary, real system metrics, verification summaries, and recent activity."""
    st.markdown("## 📊 Technician Operational Dashboard")
    st.markdown(
        "FaultSense assists elevator service technicians by synthesizing historical maintenance cases, "
        "OEM safety bulletins, and physical sensor telemetry into verified root-cause hypotheses."
    )

    kb_manager = KnowledgeBaseManager()
    kb_manager.seed_initial_data_if_empty()
    kb_stats = kb_manager.get_stats()

    inv_repo = InvestigationRepository()
    all_invs = inv_repo.list_all(limit=100)
    total_invs = len(all_invs)

    # Initialize index manager for vector metrics
    idx_mgr = IndexManager()
    idx_mgr.initialize(repo=kb_manager.repo, force_rebuild=False)
    idx_status = idx_mgr.get_status()

    # Calculate verification breakdown from actual stored investigations
    verified_count = 0
    inconclusive_count = 0
    retries_total = 0
    for inv in all_invs:
        verif = inv.get("verification_record")
        if verif and verif.get("final_status") == "verified":
            verified_count += 1
        elif inv.get("status") == "completed":
            verified_count += 1
        else:
            inconclusive_count += 1
        retries_total += int(inv.get("retry_count", 0))

    # Top Metric Cards Row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("Investigations Logged", str(total_invs), "Recorded technician sessions")
    with c2:
        kb_sub = f"{kb_stats['verified_count']} verified, {kb_stats['synthetic_count']} synthetic"
        render_metric_card("Knowledge Base Cases", str(kb_stats["total_cases"]), kb_sub)
    with c3:
        verif_rate = f"{(verified_count / max(1, total_invs) * 100):.0f}%" if total_invs > 0 else "N/A"
        render_metric_card("Verified Diagnoses", str(verified_count), f"{verif_rate} grounding rate")
    with c4:
        render_metric_card("FAISS Vector Index", str(idx_status.get("total_vectors", 0)), "384-dim all-MiniLM-L6-v2")

    # Call to action banner
    col_act1, col_act2 = st.columns([3, 1])
    with col_act1:
        st.markdown(
            """
            <div style="background: rgba(6, 182, 212, 0.08); border: 1px solid rgba(6, 182, 212, 0.3);
                        border-radius: 8px; padding: 14px 18px; margin: 8px 0 16px 0;">
                <div style="font-weight: 700; color: #38BDF8; font-size: 1.05rem;">
                    Ready to troubleshoot an elevator anomaly?
                </div>
                <div style="color: #94A3B8; font-size: 0.88rem; margin-top: 4px;">
                    Submit observed symptoms, error codes, and telemetry to trigger evidence retrieval and self-verification.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_act2:
        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
        if st.button("🚀 Start Investigation", type="primary", use_container_width=True):
            st.session_state["nav_page"] = "new_investigation"
            st.rerun()

    # Mid section: Subsystem distribution & Verification summary
    col_dist, col_verif = st.columns([1, 1])

    with col_dist:
        st.markdown("### 🏢 Monitored Subsystems")
        subsystems_data = kb_stats.get("subsystem_distribution", {})
        if subsystems_data:
            df_sub = pd.DataFrame(
                [{"Subsystem": k.replace("_", " ").title(), "Cases": v} for k, v in subsystems_data.items()]
            ).sort_values("Cases", ascending=False)
            st.dataframe(df_sub, hide_index=True, use_container_width=True)
        else:
            st.info("No cases loaded in database.")

    with col_verif:
        st.markdown("### 🛡️ Verification Performance Summary")
        if total_invs > 0:
            df_verif = pd.DataFrame([
                {"Metric": "Verified Grounded Cases", "Value": str(verified_count)},
                {"Metric": "Inconclusive / Thin Evidence", "Value": str(inconclusive_count)},
                {"Metric": "Total Refinement Retries", "Value": str(retries_total)},
                {"Metric": "Average Retries per Session", "Value": f"{(retries_total / total_invs):.1f}"},
            ])
            st.dataframe(df_verif, hide_index=True, use_container_width=True)
        else:
            st.info("No investigations logged yet. Run an investigation to generate verification metrics.")

    st.markdown("---")
    st.markdown("### 📋 Recent Diagnostic Investigations")

    recent_invs = all_invs[:5]
    if recent_invs:
        for inv in recent_invs:
            inv_id = inv.get("investigation_id", "Unknown")
            elv_id = inv.get("elevator_id", "Unknown")
            sub = str(inv.get("subsystem", "")).replace("_", " ").title()
            conf = int(float(inv.get("confidence_score", 0.0)) * 100)
            status = inv.get("status", "open")
            ts = inv.get("created_at", "")[:19].replace("T", " ")

            badge_color = "#34D399" if status == "completed" else "#F59E0B"
            with st.expander(f"**{inv_id}** — Unit: `{elv_id}` [{sub}] | Confidence: {conf}% | {ts}"):
                c_info1, c_info2 = st.columns([3, 1])
                with c_info1:
                    st.markdown(f"**Root Cause**: {inv.get('root_cause_hypothesis', 'N/A')}")
                    st.markdown(f"**Actions**: {inv.get('recommended_actions', 'N/A')}")
                with c_info2:
                    st.markdown(f"<span style='color: {badge_color}; font-weight: 700;'>● Status: {status.upper()}</span>", unsafe_allow_html=True)
                    st.caption(f"Retries: {inv.get('retry_count', 0)}")
                    if st.button(f"Inspect Results", key=f"btn_open_{inv_id}", type="secondary"):
                        st.session_state["current_investigation_id"] = inv_id
                        st.session_state["nav_page"] = "results"
                        st.rerun()
    else:
        st.info("No investigation history found. Launch a diagnostic session to populate this audit log.")
