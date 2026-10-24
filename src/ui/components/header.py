"""Header component for FaultSense UI with industrial dark navy theme."""

from datetime import datetime, timezone
import streamlit as st

from config.settings import get_settings
from src.ui.assets.logo import get_logo_html


PAGE_TITLES = {
    "overview": ("Technician Operational Dashboard", "Real-time system health, indexed vector coverage & historical telemetry"),
    "new_investigation": ("New Fault Investigation", "Intake symptoms, OEM error codes, and controller telemetry for root-cause isolation"),
    "results": ("Diagnostic Results & Verification Audit", "Evidence-grounded root-cause analysis, verification verdict, and OEM citations"),
    "assistant": ("Conversational Diagnostic Assistant", "Targeted technician follow-up Q&A grounded strictly in investigation evidence"),
    "knowledge_base": ("Elevator Fault Knowledge Base", "Verified field maintenance logs, OEM service bulletins, and FAISS indexing controls"),
    "history": ("Investigation History & Audit Trail", "Search and review past elevator investigations, verification outcomes, and exported reports"),
    "evaluation": ("RAG Evaluation & Self-Verification Benchmark", "Quantitative quality metrics comparing Baseline RAG against Self-Verifying RAG"),
    "settings": ("Settings & System Status", "Configuration parameters, secret protection masking, and live component health probes"),
}


def render_header() -> None:
    """Renders the top application branding and operational status banner."""
    settings = get_settings()
    current_page = st.session_state.get("nav_page", "overview")
    page_title, page_subtitle = PAGE_TITLES.get(current_page, ("Elevator Decision Support", ""))

    col1, col2 = st.columns([3.2, 1.3])

    with col1:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 4px;">
                <div style="flex-shrink: 0;">
                    {get_logo_html(width=48, height=44, show_text=False, dark_mode=True)}
                </div>
                <div>
                    <div style="font-size: 0.72rem; color: #06B6D4; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px;">
                        FAULT SENSE • {current_page.replace('_', ' ').upper()}
                    </div>
                    <h1 style="margin: 0; font-size: 1.55rem; font-weight: 700; color: #F8FAFC; letter-spacing: -0.3px;">
                        {page_title}
                    </h1>
                    <p style="margin: 2px 0 0 0; font-size: 0.82rem; color: #94A3B8;">
                        {page_subtitle}
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        mode_color = "#F59E0B" if settings.is_demo_mode else "#10B981"
        mode_label = "Demo / Offline Mode" if settings.is_demo_mode else "Production LLM Active"
        active_inv = st.session_state.get("current_investigation_id", "None")

        st.markdown(
            f"""
            <div style="text-align: right; padding-top: 4px;">
                <span style="background-color: {mode_color}20; color: {mode_color};
                             border: 1px solid {mode_color}60; padding: 4px 10px;
                             border-radius: 8px; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.3px;">
                    ● {mode_label}
                </span>
                <div style="font-size: 0.72rem; color: #64748B; margin-top: 4px;">
                    v{settings.app_version} | Session: <code style="color: #38BDF8; font-size: 0.72rem;">{active_inv}</code>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<hr style='margin-top: 6px; margin-bottom: 16px; border: 0; border-top: 1px solid #1E293B;'>", unsafe_allow_html=True)
