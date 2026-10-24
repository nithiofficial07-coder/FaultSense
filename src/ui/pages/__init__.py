"""FaultSense UI Pages Package."""

from src.ui.pages.assistant_page import render_assistant_page
from src.ui.pages.diagnostic_results import render_diagnostic_results_page
from src.ui.pages.evaluation import render_evaluation_page
from src.ui.pages.history import render_history_page
from src.ui.pages.knowledge_base import render_knowledge_base_page
from src.ui.pages.new_investigation import render_new_investigation_page
from src.ui.pages.overview import render_overview_page
from src.ui.pages.settings_page import render_settings_page

__all__ = [
    "render_overview_page",
    "render_new_investigation_page",
    "render_diagnostic_results_page",
    "render_assistant_page",
    "render_knowledge_base_page",
    "render_history_page",
    "render_evaluation_page",
    "render_settings_page",
]
