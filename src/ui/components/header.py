"""Header component for FaultSense UI with industrial dark navy theme."""

import streamlit as st
from config.settings import get_settings


def render_header() -> None:
    """Renders the top application branding and operational status banner."""
    settings = get_settings()

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 6px;">
                <span style="font-size: 2.2rem; filter: drop-shadow(0 0 8px rgba(6, 182, 212, 0.4));">🛗</span>
                <div>
                    <h1 style="margin: 0; font-size: 1.85rem; font-weight: 700; color: #F8FAFC; letter-spacing: -0.5px;">
                        {settings.app_name}
                    </h1>
                    <p style="margin: 2px 0 0 0; font-size: 0.9rem; color: #94A3B8;">
                        {settings.app_tagline}
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        mode_color = "#F59E0B" if settings.is_demo_mode else "#10B981"
        mode_label = "Demo / Offline Mode" if settings.is_demo_mode else "Production Active"
        st.markdown(
            f"""
            <div style="text-align: right; padding-top: 8px;">
                <span style="background-color: {mode_color}20; color: {mode_color};
                             border: 1px solid {mode_color}60; padding: 4px 10px;
                             border-radius: 8px; font-size: 0.8rem; font-weight: 600; letter-spacing: 0.3px;">
                    ● {mode_label}
                </span>
                <div style="font-size: 0.75rem; color: #64748B; margin-top: 4px;">
                    v{settings.app_version} | Non-Control System
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<hr style='margin-top: 8px; margin-bottom: 18px; border: 0; border-top: 1px solid #1E293B;'>", unsafe_allow_html=True)
