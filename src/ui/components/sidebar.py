"""Sidebar navigation and quick status component for FaultSense UI."""

import streamlit as st
from config.settings import get_settings


PAGES = [
    ("overview", "📊 Overview"),
    ("new_investigation", "🔍 New Investigation"),
    ("results", "🎯 Diagnostic Results"),
    ("assistant", "💬 Conversational Assistant"),
    ("knowledge_base", "📚 Knowledge Base"),
    ("history", "📋 Investigation History"),
    ("evaluation", "📈 Evaluation"),
    ("settings", "⚙️ Settings & Status"),
]


def render_sidebar() -> str:
    """Renders the navigation menu and returns the selected page identifier."""
    settings = get_settings()

    # Determine default page index from session state
    current_key = st.session_state.get("nav_page", "overview")
    current_idx = 0
    for idx, (k, _) in enumerate(PAGES):
        if k == current_key:
            current_idx = idx
            break

    # Synchronize radio widget state if programmatically routed
    expected_label = PAGES[current_idx][1]
    if st.session_state.get("_sidebar_radio") != expected_label:
        st.session_state["_sidebar_radio"] = expected_label


    with st.sidebar:
        st.markdown(
            """
            <div style="text-align: center; padding: 10px 0 16px 0; border-bottom: 1px solid #1E293B; margin-bottom: 14px;">
                <span style="font-size: 2.2rem; filter: drop-shadow(0 0 8px rgba(6, 182, 212, 0.4));">🛗</span>
                <h2 style="margin: 4px 0 0 0; font-size: 1.25rem; font-weight: 700; color: #F8FAFC; letter-spacing: -0.3px;">FaultSense</h2>
                <div style="font-size: 0.75rem; color: #06B6D4; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">Technician Decision Support</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='font-size: 0.75rem; text-transform: uppercase; font-weight: 700; color: #64748B; margin-bottom: 6px; letter-spacing: 0.8px;'>Main Navigation</div>", unsafe_allow_html=True)

        selected_label = st.radio(
            "Select Page",
            options=[p[1] for p in PAGES],
            label_visibility="collapsed",
            index=current_idx,
            key="_sidebar_radio",
        )

        selected_key = next(p[0] for p in PAGES if p[1] == selected_label)
        st.session_state["nav_page"] = selected_key

        st.markdown("<hr style='border: 0; border-top: 1px solid #1E293B; margin: 18px 0 12px 0;'>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.75rem; text-transform: uppercase; font-weight: 700; color: #64748B; margin-bottom: 6px; letter-spacing: 0.8px;'>Subsystem Status</div>", unsafe_allow_html=True)

        status_color = "#F59E0B" if settings.is_demo_mode else "#10B981"
        status_text = "● Offline Fallback Active" if settings.is_demo_mode else "● LLM Reasoning Active"
        st.markdown(f"<div style='color: {status_color}; font-size: 0.82rem; font-weight: 600;'>{status_text}</div>", unsafe_allow_html=True)
        st.caption(f"**Storage**: `{settings.database_path.name}`")
        st.caption(f"**Index**: `FAISS (all-MiniLM-L6-v2)`")

        # Active investigation indicator
        active_inv = st.session_state.get("current_investigation_id")
        if active_inv:
            st.markdown(
                f"""
                <div style="background: rgba(6, 182, 212, 0.1); border: 1px solid rgba(6, 182, 212, 0.3);
                            border-radius: 6px; padding: 6px 10px; margin-top: 10px;">
                    <div style="font-size: 0.7rem; color: #38BDF8; font-weight: 600; text-transform: uppercase;">Active Session</div>
                    <div style="font-size: 0.82rem; color: #F1F5F9; font-weight: 700;">{active_inv}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<hr style='border: 0; border-top: 1px solid #1E293B; margin: 18px 0 12px 0;'>", unsafe_allow_html=True)
        st.info(
            "**Safety Disclaimer**:\n"
            "FaultSense is an advisory diagnostic tool for certified vertical transportation technicians. "
            "It does NOT interface directly with elevator safety circuits or controllers.",
            icon="⚠️",
        )

    return selected_key
