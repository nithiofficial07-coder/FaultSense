"""Sidebar navigation and quick status component for FaultSense UI.

Features custom SVG branding, robust button-based stateful navigation,
active session indicator, and ASME A17.1 safety notices.
"""

from typing import Optional
import streamlit as st

from config.settings import get_settings
from src.ui.assets.logo import get_logo_html


NAV_ITEMS = [
    ("overview", "Overview", "📊", "System status & metrics"),
    ("new_investigation", "New Investigation", "🔍", "Symptom & telemetry intake"),
    ("results", "Diagnostic Results", "🎯", "Root cause & verification"),
    ("assistant", "Conversational Assistant", "💬", "Grounded technician Q&A"),
    ("knowledge_base", "Knowledge Base", "📚", "OEM cases & vector store"),
    ("history", "Investigation History", "📋", "Audit trail & past records"),
    ("evaluation", "Evaluation", "📈", "RAG comparative benchmark"),
    ("settings", "Settings & Status", "⚙️", "Configuration & health checks"),
]


def navigate_to(page_id: str, investigation_id: Optional[str] = None) -> None:
    """Safely updates routing state and triggers rerun without widget conflict."""
    st.session_state["nav_page"] = page_id
    if investigation_id:
        st.session_state["current_investigation_id"] = investigation_id
    st.rerun()


def render_sidebar() -> str:
    """Renders the navigation menu and returns the active page identifier."""
    settings = get_settings()

    # Ensure valid default page in session state
    if "nav_page" not in st.session_state:
        st.session_state["nav_page"] = "overview"

    current_page = st.session_state["nav_page"]

    with st.sidebar:
        # 1. Custom SVG Branding
        st.markdown(
            f'<div style="padding: 6px 0 14px 0; border-bottom: 1px solid #1E293B; margin-bottom: 16px; text-align: center;">{get_logo_html(width=190, height=46, show_text=True, dark_mode=True)}</div>',
            unsafe_allow_html=True,
        )

        # 2. Main Navigation Items
        st.markdown(
            "<div style='font-size: 0.72rem; text-transform: uppercase; font-weight: 700; color: #64748B; margin-bottom: 8px; letter-spacing: 0.8px;'>Main Navigation</div>",
            unsafe_allow_html=True,
        )

        for page_id, label, icon, subtext in NAV_ITEMS:
            is_active = (current_page == page_id)
            btn_class = "nav-item-btn-active" if is_active else "nav-item-btn"

            st.markdown(f'<div class="{btn_class}">', unsafe_allow_html=True)
            if st.button(
                f"{icon}  {label}",
                key=f"nav_btn_{page_id}",
                use_container_width=True,
            ):
                if current_page != page_id:
                    st.session_state["nav_page"] = page_id
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<hr style='border: 0; border-top: 1px solid #1E293B; margin: 16px 0 12px 0;'>", unsafe_allow_html=True)

        # 3. Active Session Quick-Access Card
        active_inv = st.session_state.get("current_investigation_id")
        if active_inv:
            st.markdown(
                f'<div style="background: rgba(6, 182, 212, 0.08); border: 1px solid rgba(6, 182, 212, 0.3); border-radius: 8px; padding: 10px 12px; margin-bottom: 12px;">'
                f'<div style="font-size: 0.68rem; color: #38BDF8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Active Investigation</div>'
                f'<div style="font-size: 0.88rem; color: #F8FAFC; font-weight: 700; margin-top: 2px;">{active_inv}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            c_res, c_chat = st.columns(2)
            with c_res:
                if st.button("🎯 Results", key="side_act_res", use_container_width=True):
                    navigate_to("results", active_inv)
            with c_chat:
                if st.button("💬 Chat", key="side_act_chat", use_container_width=True):
                    navigate_to("assistant", active_inv)

        # 4. Operational Status Pills
        st.markdown(
            "<div style='font-size: 0.72rem; text-transform: uppercase; font-weight: 700; color: #64748B; margin-bottom: 6px; letter-spacing: 0.8px;'>System Status</div>",
            unsafe_allow_html=True,
        )

        status_color = "#F59E0B" if settings.is_demo_mode else "#10B981"
        status_text = "● Offline Fallback Active" if settings.is_demo_mode else "● LLM Reasoning Active"
        st.markdown(
            f"<div style='color: {status_color}; font-size: 0.82rem; font-weight: 600; margin-bottom: 4px;'>{status_text}</div>",
            unsafe_allow_html=True,
        )
        st.caption(f"**Storage**: `{settings.database_path.name}`")
        st.caption(f"**Vector Store**: `FAISS (all-MiniLM-L6-v2)`")

        # 5. ASME A17.1 Safety Code Notice
        st.markdown("<hr style='border: 0; border-top: 1px solid #1E293B; margin: 14px 0 10px 0;'>", unsafe_allow_html=True)
        st.info(
            "**Safety Disclaimer**:\n"
            "FaultSense is an offline-capable advisory tool for certified vertical transportation technicians. "
            "It does NOT interface directly with elevator safety circuits, controllers, or operational relays.",
            icon="⚠️",
        )

    return st.session_state["nav_page"]
