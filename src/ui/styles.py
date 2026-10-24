"""Centralized design system and CSS stylesheet for FaultSense.

Industrial diagnostic dashboard theme:
- Dominant: Dark Navy (#0A1120, #0E1726, #131F37)
- Surface/Card: Charcoal & Slate (#1E293B, #0F172A)
- Brand Accent: Precision Cyan (#06B6D4, #38BDF8, #0284C7)
- Typography: Inter/System high-legibility sans-serif
- Accents: Emerald Green (#10B981), Amber (#F59E0B), Crimson (#EF4444)
"""

import streamlit as st


def apply_custom_styles() -> None:
    """Injects high-fidelity industrial styling into the Streamlit DOM."""
    st.markdown(
        """
        <style>
            /* Global reset & typography */
            @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

            html, body, [class*="css"] {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                color: #E2E8F0;
                background-color: #0A1120;
            }

            .main .block-container {
                padding-top: 1.2rem;
                padding-bottom: 2.8rem;
                padding-left: 2rem;
                padding-right: 2rem;
                max-width: 1440px;
            }

            /* Hide default Streamlit auto-nav & clutter */
            div[data-testid="stSidebarNav"] {
                display: none !important;
            }
            #MainMenu, footer {
                visibility: hidden;
            }

            /* Typography */
            h1, h2, h3, h4 {
                font-family: 'Outfit', sans-serif !important;
                letter-spacing: -0.02em;
            }
            h1 { font-size: 1.85rem !important; font-weight: 700 !important; color: #F8FAFC !important; }
            h2 { font-size: 1.45rem !important; font-weight: 700 !important; color: #F1F5F9 !important; margin-bottom: 0.4rem !important; }
            h3 { font-size: 1.15rem !important; font-weight: 600 !important; color: #E2E8F0 !important; }

            /* Code & Telemetry fonts */
            code, pre, .stCodeBlock {
                font-family: 'JetBrains Mono', monospace !important;
                background-color: #0A1120 !important;
                border: 1px solid #1E293B !important;
                border-radius: 6px !important;
                color: #38BDF8 !important;
            }

            /* Sidebar container */
            section[data-testid="stSidebar"] {
                background-color: #0E1726 !important;
                border-right: 1px solid #1E293B !important;
            }
            section[data-testid="stSidebar"] > div {
                padding-top: 1.2rem;
                padding-bottom: 1.5rem;
            }

            /* Sidebar navigation button item styling */
            .nav-item-btn button {
                width: 100% !important;
                text-align: left !important;
                display: flex !important;
                justify-content: flex-start !important;
                align-items: center !important;
                padding: 10px 14px !important;
                margin-bottom: 4px !important;
                background-color: transparent !important;
                border: 1px solid transparent !important;
                border-radius: 8px !important;
                color: #94A3B8 !important;
                font-weight: 500 !important;
                font-size: 0.9rem !important;
                transition: all 0.15s ease-in-out !important;
            }
            .nav-item-btn button:hover {
                background-color: #131F37 !important;
                border-color: #1E293B !important;
                color: #38BDF8 !important;
                transform: translateX(2px);
            }
            .nav-item-btn-active button {
                width: 100% !important;
                text-align: left !important;
                display: flex !important;
                justify-content: flex-start !important;
                align-items: center !important;
                padding: 10px 14px !important;
                margin-bottom: 4px !important;
                background-color: #131F37 !important;
                border: 1px solid #06B6D4 !important;
                border-left: 4px solid #06B6D4 !important;
                border-radius: 8px !important;
                color: #F8FAFC !important;
                font-weight: 700 !important;
                font-size: 0.9rem !important;
                box-shadow: 0 4px 12px rgba(6, 182, 212, 0.15) !important;
            }

            /* General Buttons */
            .stButton > button {
                border-radius: 6px !important;
                font-weight: 600 !important;
                font-size: 0.88rem !important;
                padding: 0.45rem 1rem !important;
                letter-spacing: 0.01em !important;
                transition: all 0.15s ease-in-out !important;
                border: 1px solid #1E293B !important;
            }
            .stButton > button[kind="primary"] {
                background: linear-gradient(135deg, #06B6D4 0%, #0284C7 100%) !important;
                color: #FFFFFF !important;
                border: none !important;
                box-shadow: 0 2px 10px rgba(6, 182, 212, 0.3) !important;
            }
            .stButton > button[kind="primary"]:hover {
                background: linear-gradient(135deg, #0891B2 0%, #0369A1 100%) !important;
                box-shadow: 0 4px 14px rgba(6, 182, 212, 0.45) !important;
                transform: translateY(-1px);
            }
            .stButton > button[kind="secondary"] {
                background-color: #131F37 !important;
                color: #F1F5F9 !important;
                border-color: #1E293B !important;
            }
            .stButton > button[kind="secondary"]:hover {
                border-color: #06B6D4 !important;
                color: #38BDF8 !important;
            }

            /* Form inputs & text areas */
            div[data-baseweb="input"] > div,
            div[data-baseweb="textarea"] > div,
            div[data-baseweb="select"] > div {
                background-color: #0F172A !important;
                border: 1px solid #1E293B !important;
                border-radius: 6px !important;
                color: #F1F5F9 !important;
            }
            div[data-baseweb="input"]:focus-within > div,
            div[data-baseweb="textarea"]:focus-within > div,
            div[data-baseweb="select"]:focus-within > div {
                border-color: #06B6D4 !important;
                box-shadow: 0 0 0 1px #06B6D4 !important;
            }

            /* Streamlit tabs */
            div[data-baseweb="tab-list"] {
                gap: 8px;
                border-bottom: 1px solid #1E293B !important;
                margin-bottom: 1rem;
            }
            div[data-baseweb="tab"] {
                background-color: transparent !important;
                border-radius: 6px 6px 0 0 !important;
                padding: 8px 16px !important;
                font-weight: 600 !important;
                font-size: 0.9rem !important;
                color: #94A3B8 !important;
                border: none !important;
            }
            div[data-baseweb="tab"]:hover {
                color: #38BDF8 !important;
            }
            div[aria-selected="true"][data-baseweb="tab"] {
                color: #06B6D4 !important;
                border-bottom: 2px solid #06B6D4 !important;
                background-color: rgba(6, 182, 212, 0.05) !important;
            }

            /* Expanders */
            .streamlit-expanderHeader {
                background-color: #131F37 !important;
                border: 1px solid #1E293B !important;
                border-radius: 6px !important;
                color: #F1F5F9 !important;
                font-weight: 600 !important;
            }
            .streamlit-expanderHeader:hover {
                color: #38BDF8 !important;
                border-color: #334155 !important;
            }
            div[data-testid="stExpanderDetails"] {
                background-color: #0E1726 !important;
                border: 1px solid #1E293B !important;
                border-top: none !important;
                border-radius: 0 0 6px 6px !important;
                padding: 16px !important;
            }

            /* Metric display cards */
            div[data-testid="stMetric"] {
                background-color: #131F37;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 12px 16px;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
            }
            div[data-testid="stMetricLabel"] {
                color: #94A3B8 !important;
                font-size: 0.8rem !important;
                font-weight: 600 !important;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            div[data-testid="stMetricValue"] {
                color: #F8FAFC !important;
                font-size: 1.65rem !important;
                font-weight: 700 !important;
                font-family: 'Outfit', sans-serif !important;
            }

            /* File Uploader styling */
            div[data-testid="stFileUploader"] {
                background-color: #0F172A;
                border: 1px dashed #334155;
                border-radius: 8px;
                padding: 12px;
                transition: border-color 0.2s;
            }
            div[data-testid="stFileUploader"]:hover {
                border-color: #06B6D4;
            }

            /* Dataframes & Tables */
            div[data-testid="stDataFrame"] {
                border: 1px solid #1E293B !important;
                border-radius: 8px !important;
                overflow: hidden !important;
            }

            /* Success / Warning / Error alerts */
            div[data-testid="stAlert"] {
                border-radius: 8px !important;
                padding: 12px 16px !important;
            }

            /* Custom diagnostic card containers */
            .fs-card {
                background-color: #131F37;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 14px;
            }
            .fs-card-highlight {
                background-color: #131F37;
                border: 1px solid #1E293B;
                border-left: 4px solid #06B6D4;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 14px;
            }
            .fs-card-warn {
                background-color: rgba(245, 158, 11, 0.08);
                border: 1px solid rgba(245, 158, 11, 0.3);
                border-left: 4px solid #F59E0B;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 14px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
