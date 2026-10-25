"""Settings, configuration inspector, and system health status page for FaultSense in enterprise light theme."""

import json
import streamlit as st

from config.settings import get_settings
from src.knowledge_base.manager import KnowledgeBaseManager
from src.retrieval.index_manager import IndexManager
from src.utils.health import HealthChecker


def render_settings_page() -> None:
    """Renders application configuration, secret protection status, health probes, and troubleshooting guides."""
    st.markdown("## Settings & System Status")
    st.markdown(
        "Inspect application configuration parameters, verify secret masking, probe component connectivity, "
        "and review diagnostic troubleshooting procedures."
    )

    settings = get_settings()

    # System Status Overview Cards
    kb_mgr = KnowledgeBaseManager()
    idx_mgr = IndexManager()
    idx_mgr.initialize(repo=kb_mgr.repo, force_rebuild=False)
    v_status = idx_mgr.get_status()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Database Connectivity", "Connected", f"SQLite: {settings.database_path.name}")
    with c2:
        st.metric("FAISS Vector Index", f"{v_status.get('total_vectors', 0)} Vectors", "384-dim FlatIP (Cosine)")
    with c3:
        st.metric("Embedding Model", "Active (CPU)", settings.embedding_model)
    with c4:
        mode_text = "Offline Demo" if settings.is_demo_mode else "Connected (LLM)"
        st.metric("LLM Provider Mode", mode_text, f"Provider: {settings.llm_provider}")

    st.markdown("---")

    tab_diagnostics, tab_config, tab_troubleshoot = st.tabs([
        "Live Health Diagnostics",
        "Provider & System Config",
        "Troubleshooting & Support",
    ])

    with tab_diagnostics:
        st.markdown("### Component Health Diagnostics")
        if st.button("Re-run All Health Probes", icon=":material/refresh:", type="secondary"):
            st.rerun()

        health = HealthChecker.run_all_checks()

        if health.overall_status == "healthy":
            overall_bg = "#EFF7F2"
            overall_color = "#3F7D62"
            overall_border = "#C6E2D3"
        elif health.overall_status == "degraded":
            overall_bg = "#FDF8EE"
            overall_color = "#A8752B"
            overall_border = "#EED8B4"
        else:
            overall_bg = "#FDF2F2"
            overall_color = "#B84C4C"
            overall_border = "#ECC4C4"

        st.markdown(
            f"""
            <div style="background-color: {overall_bg}; border: 1px solid {overall_border}; border-left: 4px solid {overall_color};
                        padding: 14px 20px; border-radius: 10px; margin-bottom: 16px;">
                <span style="font-size: 1.05rem; font-weight: 700; color: {overall_color};">
                    ● Overall System Health: {health.overall_status.upper()}
                </span>
                <span style="font-size: 0.85rem; color: #68778D; margin-left: 14px;">
                    Timestamp: {health.timestamp[:19].replace('T', ' ')} UTC
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for comp_name, comp_status in health.components.items():
            st_color = "#3F7D62" if comp_status.status == "healthy" else ("#A8752B" if comp_status.status == "degraded" else "#B84C4C")
            with st.expander(f"**{comp_name.title()}**: {comp_status.status.upper()} — {comp_status.message}"):
                st.markdown(f"**Status**: <span style='color: {st_color}; font-weight: 700;'>{comp_status.status.upper()}</span>", unsafe_allow_html=True)
                st.markdown(f"**Message**: {comp_status.message}")
                st.code(json.dumps(comp_status.details, indent=2), language="json")

    with tab_config:
        st.markdown("### Active Configuration (Safe Masked View)")
        st.caption("All API keys, secrets, and private credentials are automatically masked at runtime. Never exposed in logs.")

        safe_cfg = settings.get_safe_dict()

        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Application Name", value=safe_cfg["app_name"], disabled=True)
            st.text_input("Application Environment", value=safe_cfg["app_env"], disabled=True)
            st.text_input("Database Path", value=safe_cfg["database_path"], disabled=True)
            st.text_input("Log Level", value=safe_cfg["log_level"], disabled=True)
            st.text_input("LLM Provider", value=safe_cfg["llm_provider"], disabled=True)
            st.text_input("Max Verification Retries", value=str(safe_cfg.get("max_verification_retries", 2)), disabled=True)
        with col2:
            st.text_input("Application Version", value=safe_cfg["app_version"], disabled=True)
            st.text_input("Offline / Demo Mode Active", value=str(safe_cfg["demo_mode"]), disabled=True)
            st.text_input("Vector Store Type", value=safe_cfg["vector_store_type"], disabled=True)
            st.text_input("Embedding Model", value=safe_cfg["embedding_model"], disabled=True)
            st.text_input("LLM API Key (Masked)", value=safe_cfg["llm_api_key"], disabled=True)
            st.text_input("Self-Verification Enabled", value=str(safe_cfg.get("verification_enabled", False)), disabled=True)

        with st.expander("Raw Sanitized Configuration JSON"):
            st.json(safe_cfg)

    with tab_troubleshoot:
        st.markdown("### Field Troubleshooting & Operator Guidance")

        st.markdown("#### 1. Operating in Offline / Air-Gapped Environments")
        st.markdown(
            """
            When operating in machine rooms without internet connectivity:
            - FaultSense automatically engages **Deterministic Offline Fallback** for both diagnosis reasoning and evidence verification.
            - Embeddings are computed locally using the cached `all-MiniLM-L6-v2` ONNX/PyTorch model.
            - All knowledge base searches run against local SQLite and FAISS CPU indexes with zero external network traffic.
            """
        )

        st.markdown("#### 2. Re-synchronizing FAISS Vector Store")
        st.markdown(
            """
            If new records have been added to SQLite directly or the vector index appears out of date:
            1. Navigate to **Knowledge Base** -> **Vector Store (FAISS)**.
            2. Click **Rebuild Vector Index (Atomic)** to regenerate normalized embeddings for all records.
            3. Verify that total vector count equals total cases in the Knowledge Base.
            """
        )

        st.markdown("#### 3. Setting Up External LLM Providers")
        st.markdown(
            """
            To activate cloud reasoning with OpenAI, Google Gemini, or Anthropic:
            1. Set the following environment variables in your `.env` file:
               - `FAULT_SENSE_DEMO_MODE=false`
               - `FAULT_SENSE_LLM_PROVIDER=openai` (or `gemini`, `anthropic`)
               - `FAULT_SENSE_LLM_API_KEY=your_api_key_here`
               - `FAULT_SENSE_LLM_MODEL=gpt-4o-mini` (or target model)
            2. Restart the Streamlit application. Verify in **Live Health Diagnostics** that LLM connection is healthy.
            """
        )

        st.markdown("#### 4. Safety & Regulatory Boundaries")
        st.info(
            "FaultSense is classified as a Technician Decision-Support System (TDSS). "
            "Under ASME A17.1 / EN 81-20/50 regulations, software recommendations do NOT supersede certified technician "
            "judgment, physical multimeter readings, or manufacturer safety interlock protocols. "
            "Never bypass hoistway door locks or safety governor circuits."
        )
