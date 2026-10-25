"""Sidebar navigation and quick status component for FaultSense UI.

Features custom SVG branding, robust button-based stateful navigation with Material icons,
active session indicator, and ASME A17.1 safety notices in enterprise light styling.
"""

from typing import Optional
import streamlit as st
import streamlit.components.v1 as components

from config.settings import get_settings
from src.ui.assets.icons import get_icon_svg
from src.ui.assets.logo import get_logo_html
from src.utils.health import HealthChecker


NAV_ITEMS = [
    ("overview", "Overview", ":material/dashboard:", "System status & metrics"),
    ("new_investigation", "New Investigation", ":material/search:", "Symptom & telemetry intake"),
    ("results", "Diagnostic Results", ":material/analytics:", "Root cause & verification"),
    ("report", "Diagnostic Report", ":material/description:", "Download PDF & technician review"),
    ("assistant", "Conversational Assistant", ":material/chat:", "Grounded technician Q&A"),
    ("knowledge_base", "Knowledge Base", ":material/database:", "OEM cases & vector store"),
    ("history", "Investigation History", ":material/history:", "Audit trail & past records"),
    ("evaluation", "Evaluation", ":material/insights:", "RAG comparative benchmark"),
    ("settings", "Settings & Status", ":material/settings:", "Configuration & health checks"),
]


def navigate_to(page_id: str, investigation_id: Optional[str] = None) -> None:
    """Safely updates routing state and triggers rerun without widget conflict."""
    st.session_state["nav_page"] = page_id
    if investigation_id:
        st.session_state["current_investigation_id"] = investigation_id
    st.rerun()


def render_subsystem_status(settings) -> None:
    """Renders real-time subsystem status panel with pulsing animated indicators."""
    st.markdown(
        "<div style='font-size: 0.72rem; text-transform: uppercase; font-weight: 700; color: #68778D; margin-bottom: 6px; letter-spacing: 0.8px;'>Subsystem Status</div>",
        unsafe_allow_html=True,
    )

    # 1. System Mode
    is_offline = settings.is_demo_mode
    mode_text = "Offline Fallback" if is_offline else "Production LLM"
    mode_color = "#A8752B" if is_offline else "#3F7D62"
    mode_dot_class = "fs-pulse-dot-amber" if is_offline else "fs-pulse-dot-green"
    mode_tip = "Deterministic offline fallback active (zero external LLM dependency)" if is_offline else f"External provider {settings.llm_provider.upper()} connected"

    # 2. Database
    db_name = settings.database_path.name
    try:
        db_status = HealthChecker.check_database()
        db_healthy = (db_status.status == "healthy")
        case_count = db_status.details.get("case_count", 0)
        db_color = "#3F7D62" if db_healthy else "#B84C4C"
        db_dot_class = "fs-pulse-dot-green" if db_healthy else "fs-pulse-dot-red"
        db_tip = f"SQLite diagnostic store ({case_count} cases recorded)" if db_healthy else f"Database error: {db_status.message}"
    except Exception:
        db_color = "#3F7D62" if settings.database_path.exists() else "#A8752B"
        db_dot_class = "fs-pulse-dot-green" if settings.database_path.exists() else "fs-pulse-dot-amber"
        db_tip = "SQLite diagnostic repository"

    # 3. Vector Store
    try:
        vs_status = HealthChecker.check_vector_store()
        vs_healthy = (vs_status.status == "healthy")
        vec_count = vs_status.details.get("vector_count", 0)
        vs_color = "#3F7D62" if vs_healthy else "#A8752B"
        vs_dot_class = "fs-pulse-dot-green" if vs_healthy else "fs-pulse-dot-amber"
        vs_tip = f"FAISS similarity index ({vec_count} vectors loaded)" if vs_healthy else "FAISS index uninitialized"
    except Exception:
        vs_color = "#3F7D62"
        vs_dot_class = "fs-pulse-dot-green"
        vs_tip = "FAISS vector store active"

    # 4. Embedding Model
    emb_full = settings.embedding_model
    emb_model = emb_full.split("/")[-1] if "/" in emb_full else emb_full
    emb_tip = "384-dimensional dense sentence embeddings (all-MiniLM-L6-v2)"

    icon_cpu = get_icon_svg("cpu", size=13, color="#68778D")
    icon_db = get_icon_svg("hard_drive", size=13, color="#68778D")
    icon_vec = get_icon_svg("compass", size=13, color="#68778D")
    icon_emb = get_icon_svg("layers", size=13, color="#68778D")

    panel_html = (
        f'<div class="fs-status-panel">'
        f'<div class="fs-status-row" title="{mode_tip}">'
        f'<span class="fs-status-label"><span class="fs-status-icon">{icon_cpu}</span><span>System Mode</span></span>'
        f'<span class="fs-status-value" style="color: {mode_color};"><span class="fs-pulse-dot {mode_dot_class}"></span><span>{mode_text}</span></span>'
        f'</div>'
        f'<div class="fs-status-row" title="{db_tip}">'
        f'<span class="fs-status-label"><span class="fs-status-icon">{icon_db}</span><span>Database</span></span>'
        f'<span class="fs-status-value" style="color: {db_color};"><span class="fs-pulse-dot {db_dot_class}"></span><code>{db_name}</code></span>'
        f'</div>'
        f'<div class="fs-status-row" title="{vs_tip}">'
        f'<span class="fs-status-label"><span class="fs-status-icon">{icon_vec}</span><span>Vector Store</span></span>'
        f'<span class="fs-status-value" style="color: {vs_color};"><span class="fs-pulse-dot {vs_dot_class}"></span><code>FAISS</code></span>'
        f'</div>'
        f'<div class="fs-status-row" title="{emb_tip}">'
        f'<span class="fs-status-label"><span class="fs-status-icon">{icon_emb}</span><span>Embedding Model</span></span>'
        f'<span class="fs-status-value" style="color: #4169A8;"><code>{emb_model}</code></span>'
        f'</div>'
        f'</div>'
    )
    st.markdown(panel_html, unsafe_allow_html=True)


def render_safety_disclaimer() -> None:
    """Renders the enterprise safety information card and compliance expander in light theme."""
    icon_shield = get_icon_svg("shield_alert", size=15, color="#A8752B")
    disclaimer_html = (
        f'<div class="fs-disclaimer-card">'
        f'<div class="fs-disclaimer-header">'
        f'<span class="fs-disclaimer-icon">{icon_shield}</span>'
        f'<span class="fs-disclaimer-title">Safety &amp; Operational Limitations</span>'
        f'</div>'
        f'<p class="fs-disclaimer-body">'
        f'FaultSense is an advisory decision-support tool for qualified elevator maintenance personnel. '
        f'It does not directly control elevators, operate safety circuits, or perform repairs. '
        f'All diagnostic recommendations must be verified by qualified personnel using approved procedures and manufacturer documentation.'
        f'</p>'
        f'</div>'
    )
    st.markdown(disclaimer_html, unsafe_allow_html=True)

    with st.expander("Read safety details"):
        st.markdown(
            f'<div style="font-size: 0.74rem; color: #55657E; line-height: 1.45;">'
            f'<div style="margin-bottom: 4px;"><b style="color: #243247;">• ASME A17.1 / CSA B44</b>: Advisory only; never bypasses or overrides hoistway interlocks, car gate switches, or safety chains.</div>'
            f'<div style="margin-bottom: 4px;"><b style="color: #243247;">• LOTO Protocol</b>: Certified Lockout/Tagout of main disconnect switches required before entering hoistway or car top.</div>'
            f'<div><b style="color: #243247;">• Dual Verification</b>: Critical brake torque and traction tests require physical mechanical verification before return to service.</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def render_cursor_pointer_script() -> None:
    """Injects a smooth, non-intrusive cursor-following pointer inside the sidebar navigation."""
    script_html = """
    <script>
    (function() {
        try {
            // Respect accessibility reduced-motion preference
            if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                return;
            }
            // Disable on touch devices
            if ('ontouchstart' in window || (navigator.maxTouchPoints && navigator.maxTouchPoints > 0)) {
                return;
            }

            const doc = window.parent.document;
            if (!doc) return;

            // Ensure pointer element exists in main document body
            let pointer = doc.getElementById('fs-sidebar-pointer');
            if (!pointer) {
                pointer = doc.createElement('div');
                pointer.id = 'fs-sidebar-pointer';
                pointer.setAttribute('aria-hidden', 'true');
                doc.body.appendChild(pointer);
            }

            const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
            if (!sidebar || sidebar.dataset.fsPointerReady) return;
            sidebar.dataset.fsPointerReady = 'true';

            let curX = 0, curY = 0;
            let targetX = 0, targetY = 0;
            let isVisible = false;

            function animate() {
                if (isVisible) {
                    curX += (targetX - curX) * 0.24;
                    curY += (targetY - curY) * 0.24;
                    pointer.style.left = curX.toFixed(1) + 'px';
                    pointer.style.top = curY.toFixed(1) + 'px';
                }
                requestAnimationFrame(animate);
            }
            requestAnimationFrame(animate);

            sidebar.addEventListener('mouseenter', function(e) {
                targetX = e.clientX;
                targetY = e.clientY;
                curX = targetX;
                curY = targetY;
                pointer.style.left = curX + 'px';
                pointer.style.top = curY + 'px';
                isVisible = true;
                pointer.classList.add('fs-pointer-visible');
            });

            sidebar.addEventListener('mousemove', function(e) {
                targetX = e.clientX;
                targetY = e.clientY;
                if (!isVisible) {
                    isVisible = true;
                    pointer.classList.add('fs-pointer-visible');
                }
            });

            sidebar.addEventListener('mouseleave', function() {
                isVisible = false;
                pointer.classList.remove('fs-pointer-visible');
            });
        } catch (err) {
            // Graceful fallback without impacting navigation
        }
    })();
    </script>
    """
    components.html(script_html, height=0)


def render_sidebar() -> str:
    """Renders the navigation menu and returns the active page identifier."""
    settings = get_settings()

    # Ensure valid default page in session state
    if "nav_page" not in st.session_state:
        st.session_state["nav_page"] = "overview"

    current_page = st.session_state["nav_page"]

    with st.sidebar:
        # 1. Compact Custom SVG Branding
        st.markdown(
            f'<div style="padding: 4px 0 10px 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 12px; text-align: center;">{get_logo_html(width=172, height=42, show_text=True, dark_mode=False)}</div>',
            unsafe_allow_html=True,
        )

        # 2. Main Navigation Items (Clean, compact hierarchy)
        st.markdown(
            "<div style='font-size: 0.72rem; text-transform: uppercase; font-weight: 700; color: #718096; margin-bottom: 6px; letter-spacing: 0.8px; padding-left: 2px;'>Navigation</div>",
            unsafe_allow_html=True,
        )

        for page_id, label, icon_name, subtext in NAV_ITEMS:
            is_active = (current_page == page_id)
            if st.button(
                label,
                key=f"nav_btn_{page_id}",
                icon=icon_name,
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                if current_page != page_id:
                    st.session_state["nav_page"] = page_id
                    st.rerun()

        # Inject non-intrusive cursor-following pointer script
        render_cursor_pointer_script()

        st.markdown("<hr style='border: 0; border-top: 1px solid #E2E8F0; margin: 12px 0 10px 0;'>", unsafe_allow_html=True)

        # 3. Active Session Quick-Access Card
        active_inv = st.session_state.get("current_investigation_id")
        if active_inv:
            st.markdown(
                f'<div style="background: #EAF1FA; border: 1px solid #CADDF5; border-radius: 8px; padding: 8px 12px; margin-bottom: 10px;">'
                f'<div style="font-size: 0.68rem; color: #4169A8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Active Investigation</div>'
                f'<div style="font-size: 0.84rem; color: #27364B; font-weight: 700; margin-top: 2px;">{active_inv}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            c_res, c_rep, c_chat = st.columns(3)
            with c_res:
                if st.button("Results", key="side_act_res", icon=":material/analytics:", use_container_width=True):
                    navigate_to("results", active_inv)
            with c_rep:
                if st.button("Report", key="side_act_rep", icon=":material/description:", use_container_width=True):
                    navigate_to("report", active_inv)
            with c_chat:
                if st.button("Chat", key="side_act_chat", icon=":material/chat:", use_container_width=True):
                    navigate_to("assistant", active_inv)

        # 4. Subsystem Status Panel
        render_subsystem_status(settings)

        # 5. Professional Safety Disclaimer Card
        render_safety_disclaimer()

    return st.session_state["nav_page"]
