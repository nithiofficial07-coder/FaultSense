"""FaultSense - Autonomous Fault Isolation and Root Cause Analysis Assistant.

Main Streamlit Application Shell with Dark Navy Industrial Diagnostic Theme.
"""

import streamlit as st

from config.settings import get_settings
from src.ui.components.header import render_header
from src.ui.components.sidebar import render_sidebar
from src.ui.pages.assistant_page import render_assistant_page
from src.ui.pages.diagnostic_report import render_diagnostic_report_page
from src.ui.pages.diagnostic_results import render_diagnostic_results_page
from src.ui.pages.evaluation import render_evaluation_page
from src.ui.pages.history import render_history_page
from src.ui.pages.knowledge_base import render_knowledge_base_page
from src.ui.pages.new_investigation import render_new_investigation_page
from src.ui.pages.overview import render_overview_page
from src.ui.pages.settings_page import render_settings_page
from src.ui.styles import apply_custom_styles
from src.utils.logger import get_logger, setup_logging

# Initialize logging infrastructure at application boot
setup_logging()
logger = get_logger("app")

# Page Configuration
settings = get_settings()
st.set_page_config(
    page_title=f"{settings.app_name} - Elevator RCA Assistant",
    page_icon="🛗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply Centralized Industrial Dark Navy & Cyan Design System
apply_custom_styles()


def main() -> None:
    """Main routing and shell controller."""
    # Top branding and operational status banner
    render_header()

    # Sidebar navigation
    selected_page = render_sidebar()

    # Page Routing
    if selected_page == "overview":
        render_overview_page()
    elif selected_page == "new_investigation":
        render_new_investigation_page()
    elif selected_page == "results":
        render_diagnostic_results_page()
    elif selected_page == "report":
        render_diagnostic_report_page()
    elif selected_page == "assistant":
        render_assistant_page()
    elif selected_page == "knowledge_base":
        render_knowledge_base_page()
    elif selected_page == "history":
        render_history_page()
    elif selected_page == "evaluation":
        render_evaluation_page()
    elif selected_page == "settings":
        render_settings_page()
    else:
        render_overview_page()


if __name__ == "__main__":
    main()
