"""Centralized design system and CSS stylesheet for FaultSense.

Enterprise diagnostic light theme:
- Main background: #F5F7FA
- Sidebar background: #FFFFFF
- Cards and content panels: #FFFFFF
- Primary text: #1F2937
- Secondary text: #64748B
- Primary brand accent: #2563EB
- Borders and dividers: #E2E8F0
- Subtle selected background: #EFF6FF
- Status colors: Success #15803D, Warning #B45309, Error #B91C1C, Info #0369A1
"""

import streamlit as st


def apply_custom_styles() -> None:
    """Injects high-fidelity enterprise light styling into the Streamlit DOM."""
    st.markdown(
        """
        <style>
            /* Global reset & typography */
            @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

            html, body, [class*="css"] {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                color: #1F2937;
                background-color: #F5F7FA;
            }

            .stApp {
                background-color: #F5F7FA !important;
                color: #1F2937 !important;
            }

            .main .block-container {
                padding-top: 1.2rem;
                padding-bottom: 2.8rem;
                padding-left: 2rem;
                padding-right: 2rem;
                max-width: 1440px;
                background-color: #F5F7FA;
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
                color: #1F2937 !important;
            }
            h1 { font-size: 1.85rem !important; font-weight: 700 !important; }
            h2 { font-size: 1.45rem !important; font-weight: 700 !important; margin-bottom: 0.4rem !important; }
            h3 { font-size: 1.15rem !important; font-weight: 600 !important; }
            p, span, label, div {
                color: #1F2937;
            }

            /* Code & Telemetry fonts */
            code, pre, .stCodeBlock {
                font-family: 'JetBrains Mono', monospace !important;
                background-color: #F8FAFC !important;
                border: 1px solid #E2E8F0 !important;
                border-radius: 6px !important;
                color: #0F172A !important;
            }

            /* Sidebar container */
            section[data-testid="stSidebar"] {
                background-color: #FFFFFF !important;
                border-right: 1px solid #E2E8F0 !important;
            }
            section[data-testid="stSidebar"] > div {
                padding-top: 1.2rem;
                padding-bottom: 1.5rem;
                background-color: #FFFFFF !important;
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
                color: #475569 !important;
                font-weight: 500 !important;
                font-size: 0.9rem !important;
                transition: all 0.15s ease-in-out !important;
            }
            .nav-item-btn button:hover {
                background-color: #F1F5F9 !important;
                border-color: #E2E8F0 !important;
                color: #1E293B !important;
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
                background-color: #EFF6FF !important;
                border: 1px solid #BFDBFE !important;
                border-left: 4px solid #2563EB !important;
                border-radius: 8px !important;
                color: #1E40AF !important;
                font-weight: 700 !important;
                font-size: 0.9rem !important;
                box-shadow: 0 1px 3px rgba(37, 99, 235, 0.08) !important;
            }

            /* General Buttons */
            .stButton > button {
                border-radius: 6px !important;
                font-weight: 600 !important;
                font-size: 0.88rem !important;
                padding: 0.45rem 1rem !important;
                letter-spacing: 0.01em !important;
                transition: all 0.15s ease-in-out !important;
                border: 1px solid #CBD5E1 !important;
                background-color: #FFFFFF !important;
                color: #1F2937 !important;
            }
            .stButton > button:hover {
                background-color: #F8FAFC !important;
                border-color: #94A3B8 !important;
                color: #0F172A !important;
            }
            .stButton > button[kind="primary"] {
                background: #2563EB !important;
                color: #FFFFFF !important;
                border: 1px solid #1D4ED8 !important;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
            }
            .stButton > button[kind="primary"]:hover {
                background: #1D4ED8 !important;
                border-color: #1E40AF !important;
                box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2) !important;
                transform: translateY(-1px);
            }
            .stButton > button[kind="secondary"] {
                background-color: #FFFFFF !important;
                color: #1F2937 !important;
                border: 1px solid #CBD5E1 !important;
            }
            .stButton > button[kind="secondary"]:hover {
                background-color: #F8FAFC !important;
                border-color: #94A3B8 !important;
                color: #2563EB !important;
            }

            /* Form inputs, select boxes, text areas */
            div[data-baseweb="input"] > div,
            div[data-baseweb="textarea"] > div,
            div[data-baseweb="select"] > div {
                background-color: #FFFFFF !important;
                border: 1px solid #CBD5E1 !important;
                border-radius: 6px !important;
                color: #1F2937 !important;
            }
            div[data-baseweb="input"]:focus-within > div,
            div[data-baseweb="textarea"]:focus-within > div,
            div[data-baseweb="select"]:focus-within > div {
                border-color: #2563EB !important;
                box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12) !important;
            }
            div[data-baseweb="input"] input,
            div[data-baseweb="textarea"] textarea {
                color: #1F2937 !important;
                background-color: #FFFFFF !important;
            }

            /* Streamlit tabs */
            div[data-baseweb="tab-list"] {
                gap: 8px;
                border-bottom: 1px solid #E2E8F0 !important;
                margin-bottom: 1rem;
            }
            div[data-baseweb="tab"] {
                background-color: transparent !important;
                border-radius: 6px 6px 0 0 !important;
                padding: 8px 16px !important;
                font-weight: 600 !important;
                font-size: 0.9rem !important;
                color: #64748B !important;
                border: none !important;
            }
            div[data-baseweb="tab"]:hover {
                color: #1F2937 !important;
            }
            div[aria-selected="true"][data-baseweb="tab"] {
                color: #2563EB !important;
                border-bottom: 2px solid #2563EB !important;
                background-color: #EFF6FF !important;
            }

            /* Expanders */
            .streamlit-expanderHeader {
                background-color: #F8FAFC !important;
                border: 1px solid #E2E8F0 !important;
                border-radius: 6px !important;
                color: #1F2937 !important;
                font-weight: 600 !important;
            }
            .streamlit-expanderHeader:hover {
                color: #2563EB !important;
                border-color: #CBD5E1 !important;
            }
            div[data-testid="stExpanderDetails"] {
                background-color: #FFFFFF !important;
                border: 1px solid #E2E8F0 !important;
                border-top: none !important;
                border-radius: 0 0 6px 6px !important;
                padding: 16px !important;
            }

            /* Metric display cards */
            div[data-testid="stMetric"] {
                background-color: #FFFFFF !important;
                border: 1px solid #E2E8F0 !important;
                border-radius: 8px !important;
                padding: 14px 18px !important;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
            }
            div[data-testid="stMetricLabel"] {
                color: #64748B !important;
                font-size: 0.78rem !important;
                font-weight: 600 !important;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            div[data-testid="stMetricValue"] {
                color: #1F2937 !important;
                font-size: 1.65rem !important;
                font-weight: 700 !important;
                font-family: 'Outfit', sans-serif !important;
            }

            /* File Uploader styling */
            div[data-testid="stFileUploader"] {
                background-color: #FFFFFF !important;
                border: 1px dashed #CBD5E1 !important;
                border-radius: 8px !important;
                padding: 16px !important;
                transition: border-color 0.2s;
            }
            div[data-testid="stFileUploader"]:hover {
                border-color: #2563EB !important;
            }

            /* Dataframes & Tables */
            div[data-testid="stDataFrame"] {
                border: 1px solid #E2E8F0 !important;
                border-radius: 8px !important;
                background-color: #FFFFFF !important;
                overflow: hidden !important;
            }

            /* Alerts & Notification Banners */
            div[data-testid="stAlert"] {
                border-radius: 8px !important;
                padding: 12px 16px !important;
                font-size: 0.9rem !important;
            }

            /* Custom diagnostic card containers */
            .fs-card {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 18px;
                margin-bottom: 14px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
            }
            .fs-card-highlight {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-left: 4px solid #2563EB;
                border-radius: 8px;
                padding: 18px;
                margin-bottom: 14px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
            }
            .fs-card-warn {
                background-color: #FFFBEB;
                border: 1px solid #FDE68A;
                border-left: 4px solid #B45309;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 14px;
            }
            .fs-card-info {
                background-color: #F0F9FF;
                border: 1px solid #BAE6FD;
                border-left: 4px solid #0369A1;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 14px;
            }

            /* Subsystem Status Panel in Sidebar */
            .fs-status-panel {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 10px 14px;
                margin-bottom: 14px;
            }
            .fs-status-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 7px 0;
                font-size: 0.78rem;
                border-bottom: 1px solid #E2E8F0;
            }
            .fs-status-row:last-child {
                border-bottom: none;
                padding-bottom: 2px;
            }
            .fs-status-row:first-child {
                padding-top: 2px;
            }
            .fs-status-label {
                display: flex;
                align-items: center;
                gap: 7px;
                color: #64748B;
                font-weight: 500;
            }
            .fs-status-icon {
                display: inline-flex;
                align-items: center;
                color: #64748B;
            }
            .fs-status-value {
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.75rem;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 6px;
                color: #1F2937;
            }

            /* Animated Pulse Indicators */
            @keyframes fs-pulse {
                0% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.4; transform: scale(0.85); }
                100% { opacity: 1; transform: scale(1); }
            }
            .fs-pulse-dot {
                display: inline-block;
                width: 7px;
                height: 7px;
                border-radius: 50%;
                animation: fs-pulse 2.2s ease-in-out infinite;
            }
            .fs-pulse-dot-amber {
                background-color: #B45309;
                box-shadow: 0 0 4px rgba(180, 83, 9, 0.4);
            }
            .fs-pulse-dot-green {
                background-color: #15803D;
                box-shadow: 0 0 4px rgba(21, 128, 61, 0.4);
            }
            .fs-pulse-dot-red {
                background-color: #B91C1C;
                box-shadow: 0 0 4px rgba(185, 28, 28, 0.4);
            }

            /* Professional Safety Disclaimer Card */
            .fs-disclaimer-card {
                background-color: #FFFBEB;
                border: 1px solid #FDE68A;
                border-left: 3px solid #B45309;
                border-radius: 8px;
                padding: 12px 14px;
                margin-top: 8px;
                margin-bottom: 6px;
            }
            .fs-disclaimer-header {
                display: flex;
                align-items: center;
                gap: 7px;
                margin-bottom: 5px;
            }
            .fs-disclaimer-icon {
                display: inline-flex;
                align-items: center;
                color: #B45309;
            }
            .fs-disclaimer-title {
                font-size: 0.77rem;
                font-weight: 700;
                color: #92400E;
                letter-spacing: 0.3px;
                text-transform: uppercase;
            }
            .fs-disclaimer-body {
                font-size: 0.77rem;
                line-height: 1.45;
                color: #78350F;
                margin: 0;
            }

            /* Inline Icon Styling */
            .fs-icon {
                vertical-align: -0.22em;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
