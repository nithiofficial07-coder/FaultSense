"""Reusable card and badge components for FaultSense UI with enterprise light theme."""

from typing import Optional
import streamlit as st

from src.ui.assets.icons import get_icon_svg, icon_badge


def render_metric_card(
    label: str, value: str, subtext: Optional[str] = None, delta_color: str = "normal"
) -> None:
    """Renders a styled enterprise metric card with white background and blue accent."""
    subtext_html = (
        f"<div style='font-size: 0.78rem; color: #64748B; margin-top: 4px;'>{subtext}</div>"
        if subtext
        else ""
    )
    st.markdown(
        f'<div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-left: 3px solid #2563EB; border-radius: 8px; padding: 14px 16px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">'
        f'<div style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase; color: #64748B; letter-spacing: 0.6px;">{label}</div>'
        f'<div style="font-size: 1.85rem; font-weight: 700; color: #1F2937; margin-top: 4px; line-height: 1.2;">{value}</div>'
        f'{subtext_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_status_badge(status: str) -> str:
    """Returns an accessible HTML badge with Lucide icon for verification status."""
    st_clean = status.lower().strip()
    if st_clean == "verified":
        return icon_badge("check_circle", "Verified Incident", variant="success")
    elif st_clean == "synthetic":
        return icon_badge("cpu", "Synthetic Benchmark", variant="info")
    else:
        return icon_badge("alert_triangle", "Unverified Record", variant="warning")
