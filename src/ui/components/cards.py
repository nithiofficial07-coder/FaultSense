"""Reusable card and badge components for FaultSense UI with industrial dark navy theme."""

from typing import Optional
import streamlit as st


def render_metric_card(
    label: str, value: str, subtext: Optional[str] = None, delta_color: str = "normal"
) -> None:
    """Renders a styled industrial metric card with dark navy background and cyan accents."""
    subtext_html = (
        f"<div style='font-size: 0.78rem; color: #94A3B8; margin-top: 4px;'>{subtext}</div>"
        if subtext
        else ""
    )
    st.markdown(
        f'<div style="background-color: #131F37; border: 1px solid #1E293B; border-left: 3px solid #06B6D4; border-radius: 8px; padding: 14px 16px; margin-bottom: 12px;">'
        f'<div style="font-size: 0.78rem; font-weight: 600; text-transform: uppercase; color: #38BDF8; letter-spacing: 0.6px;">{label}</div>'
        f'<div style="font-size: 1.85rem; font-weight: 700; color: #F8FAFC; margin-top: 4px; line-height: 1.2;">{value}</div>'
        f'{subtext_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_status_badge(status: str) -> str:
    """Returns an HTML badge for a verification status with dark theme contrast."""
    st_clean = status.lower().strip()
    if st_clean == "verified":
        return "<span style='background-color: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.4); padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600;'>✓ Verified Incident</span>"
    elif st_clean == "synthetic":
        return "<span style='background-color: rgba(6, 182, 212, 0.15); color: #38BDF8; border: 1px solid rgba(6, 182, 212, 0.4); padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600;'>⚡ Synthetic Benchmark</span>"
    else:
        return "<span style='background-color: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.4); padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600;'>? Unverified Record</span>"
