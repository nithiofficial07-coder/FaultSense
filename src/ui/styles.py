"""Centralized design system and CSS stylesheet for FaultSense.

Enterprise diagnostic light theme — Soft Slate + Muted Blue + Sage:
- Main page background: #F6F8FB
- Sidebar background: #FFFFFF
- Cards and content panels: #FFFFFF
- Primary text: #243247
- Secondary text: #68778D
- Primary accent: #4169A8
- Primary accent hover: #34558B
- Subtle accent background: #EAF1FA
- Borders and dividers: #E2E8F0
- Hover background: #F0F4F9
- Active navigation background: #E8EFF9
- Success: #3F7D62 (Sage green)
- Warning: #A8752B (Amber)
- Error: #B84C4C (Muted red)
- Information: #477AA5
"""

import streamlit as st


def apply_custom_styles() -> None:
    """Injects high-fidelity enterprise light styling into the Streamlit DOM."""
    st.markdown(
        """
        <style>
            /* Design Tokens */
            :root {
                --fs-bg-main: #F6F8FB;
                --fs-bg-sidebar: #FFFFFF;
                --fs-bg-card: #FFFFFF;
                --fs-text-primary: #243247;
                --fs-text-secondary: #68778D;
                --fs-accent-primary: #4169A8;
                --fs-accent-hover: #34558B;
                --fs-accent-subtle: #EAF1FA;
                --fs-border-subtle: #E2E8F0;
                --fs-bg-hover: #F0F4F9;
                --fs-nav-active: #E8EFF9;
                --fs-success: #3F7D62;
                --fs-success-bg: #EFF7F2;
                --fs-success-border: #C6E2D3;
                --fs-warning: #A8752B;
                --fs-warning-bg: #FDF8EE;
                --fs-warning-border: #EED8B4;
                --fs-error: #B84C4C;
                --fs-error-bg: #FDF2F2;
                --fs-error-border: #ECC4C4;
                --fs-info: #477AA5;
                --fs-info-bg: #EDF4F9;
                --fs-info-border: #C8DFEF;

                --space-1: 4px;
                --space-2: 8px;
                --space-3: 12px;
                --space-4: 16px;
                --space-5: 24px;
                --space-6: 32px;
            }

            /* Global reset & typography */
            @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

            html, body, [class*="css"] {
                font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                color: #243247;
                background-color: #F6F8FB;
                line-height: 1.55;
            }

            .stApp {
                background-color: #F6F8FB !important;
                color: #243247 !important;
            }

            .main .block-container {
                padding-top: 1.25rem;
                padding-bottom: 3rem;
                padding-left: 2rem;
                padding-right: 2rem;
                max-width: 1400px;
                background-color: #F6F8FB;
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
                font-family: 'Outfit', 'Inter', sans-serif !important;
                letter-spacing: -0.02em;
                color: #243247 !important;
            }
            h1 { font-size: 1.85rem !important; font-weight: 700 !important; line-height: 1.3 !important; }
            h2 { font-size: 1.4rem !important; font-weight: 700 !important; margin-bottom: 0.5rem !important; line-height: 1.3 !important; }
            h3 { font-size: 1.12rem !important; font-weight: 600 !important; margin-top: 0.75rem !important; margin-bottom: 0.4rem !important; }
            p, span, label, div {
                color: #243247;
            }

            /* Code & Telemetry fonts */
            code, pre, .stCodeBlock {
                font-family: 'JetBrains Mono', monospace !important;
                background-color: #F8FAFC !important;
                border: 1px solid #E2E8F0 !important;
                border-radius: 6px !important;
                color: #243247 !important;
            }

            /* Sidebar container */
            section[data-testid="stSidebar"] {
                background-color: #FFFFFF !important;
                border-right: 1px solid #E2E8F0 !important;
            }
            section[data-testid="stSidebar"] > div {
                padding-top: 1.2rem;
                padding-bottom: 1.8rem;
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
                margin-bottom: 3px !important;
                background-color: transparent !important;
                border: 1px solid transparent !important;
                border-radius: 8px !important;
                color: #55657E !important;
                font-weight: 500 !important;
                font-size: 0.88rem !important;
                transition: all 0.15s ease-in-out !important;
            }
            .nav-item-btn button:hover {
                background-color: #F0F4F9 !important;
                border-color: #E2E8F0 !important;
                color: #243247 !important;
                transform: translateX(2px);
            }
            .nav-item-btn-active button {
                width: 100% !important;
                text-align: left !important;
                display: flex !important;
                justify-content: flex-start !important;
                align-items: center !important;
                padding: 10px 14px !important;
                margin-bottom: 3px !important;
                background-color: #E8EFF9 !important;
                border: 1px solid #C4D7F0 !important;
                border-left: 4px solid #4169A8 !important;
                border-radius: 8px !important;
                color: #243F6C !important;
                font-weight: 700 !important;
                font-size: 0.88rem !important;
                box-shadow: 0 1px 2px rgba(65, 105, 168, 0.08) !important;
            }

            /* General Buttons */
            .stButton > button {
                border-radius: 8px !important;
                font-weight: 600 !important;
                font-size: 0.88rem !important;
                padding: 0.5rem 1.1rem !important;
                min-height: 40px !important;
                letter-spacing: 0.01em !important;
                transition: all 0.15s ease-in-out !important;
                border: 1px solid #CBD5E1 !important;
                background-color: #FFFFFF !important;
                color: #243247 !important;
                cursor: pointer !important;
            }
            .stButton > button:hover {
                background-color: #F0F4F9 !important;
                border-color: #A6B7CC !important;
                color: #1A2636 !important;
            }
            .stButton > button[kind="primary"] {
                background: #4169A8 !important;
                color: #FFFFFF !important;
                border: 1px solid #34558B !important;
                box-shadow: 0 1px 3px rgba(65, 105, 168, 0.18) !important;
            }
            .stButton > button[kind="primary"]:hover {
                background: #34558B !important;
                border-color: #2A4570 !important;
                box-shadow: 0 2px 5px rgba(65, 105, 168, 0.28) !important;
                transform: translateY(-1px);
            }
            .stButton > button[kind="secondary"] {
                background-color: #FFFFFF !important;
                color: #243247 !important;
                border: 1px solid #CBD5E1 !important;
            }
            .stButton > button[kind="secondary"]:hover {
                background-color: #F0F4F9 !important;
                border-color: #4169A8 !important;
                color: #4169A8 !important;
            }
            .stButton > button:disabled {
                opacity: 0.55 !important;
                cursor: not-allowed !important;
            }

            /* Download Buttons */
            .stDownloadButton > button {
                border-radius: 8px !important;
                font-weight: 600 !important;
                font-size: 0.88rem !important;
                padding: 0.5rem 1.1rem !important;
                min-height: 40px !important;
                transition: all 0.15s ease-in-out !important;
                border: 1px solid #CBD5E1 !important;
                background-color: #FFFFFF !important;
                color: #243247 !important;
            }
            .stDownloadButton > button:hover {
                background-color: #F0F4F9 !important;
                border-color: #4169A8 !important;
                color: #4169A8 !important;
            }
            .stDownloadButton > button[kind="primary"] {
                background: #4169A8 !important;
                color: #FFFFFF !important;
                border: 1px solid #34558B !important;
            }
            .stDownloadButton > button[kind="primary"]:hover {
                background: #34558B !important;
            }

            /* Form inputs, select boxes, text areas */
            div[data-baseweb="input"] > div,
            div[data-baseweb="textarea"] > div,
            div[data-baseweb="select"] > div {
                background-color: #FFFFFF !important;
                border: 1px solid #CBD5E1 !important;
                border-radius: 8px !important;
                color: #243247 !important;
                min-height: 42px !important;
            }
            div[data-baseweb="input"]:focus-within > div,
            div[data-baseweb="textarea"]:focus-within > div,
            div[data-baseweb="select"]:focus-within > div {
                border-color: #4169A8 !important;
                box-shadow: 0 0 0 3px rgba(65, 105, 168, 0.15) !important;
            }
            div[data-baseweb="input"] input,
            div[data-baseweb="textarea"] textarea {
                color: #243247 !important;
                background-color: #FFFFFF !important;
                font-size: 0.9rem !important;
            }
            div[data-testid="stWidgetLabel"] label {
                font-weight: 600 !important;
                color: #243247 !important;
                font-size: 0.88rem !important;
                margin-bottom: 4px !important;
            }

            /* Streamlit tabs */
            div[data-baseweb="tab-list"] {
                gap: 8px;
                border-bottom: 1px solid #E2E8F0 !important;
                margin-bottom: 1.25rem;
            }
            div[data-baseweb="tab"] {
                background-color: transparent !important;
                border-radius: 8px 8px 0 0 !important;
                padding: 10px 18px !important;
                font-weight: 600 !important;
                font-size: 0.9rem !important;
                color: #68778D !important;
                border: none !important;
            }
            div[data-baseweb="tab"]:hover {
                color: #243247 !important;
                background-color: #F0F4F9 !important;
            }
            div[aria-selected="true"][data-baseweb="tab"] {
                color: #4169A8 !important;
                border-bottom: 2px solid #4169A8 !important;
                background-color: #EAF1FA !important;
            }

            /* Expanders */
            .streamlit-expanderHeader {
                background-color: #FFFFFF !important;
                border: 1px solid #E2E8F0 !important;
                border-radius: 8px !important;
                color: #243247 !important;
                font-weight: 600 !important;
                padding: 12px 16px !important;
            }
            .streamlit-expanderHeader:hover {
                color: #4169A8 !important;
                border-color: #CBD5E1 !important;
                background-color: #F0F4F9 !important;
            }
            div[data-testid="stExpanderDetails"] {
                background-color: #FFFFFF !important;
                border: 1px solid #E2E8F0 !important;
                border-top: none !important;
                border-radius: 0 0 8px 8px !important;
                padding: 18px !important;
            }

            /* Metric display cards */
            div[data-testid="stMetric"] {
                background-color: #FFFFFF !important;
                border: 1px solid #E2E8F0 !important;
                border-radius: 10px !important;
                padding: 16px 20px !important;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03) !important;
            }
            div[data-testid="stMetricLabel"] {
                color: #68778D !important;
                font-size: 0.78rem !important;
                font-weight: 600 !important;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            div[data-testid="stMetricValue"] {
                color: #243247 !important;
                font-size: 1.65rem !important;
                font-weight: 700 !important;
                font-family: 'Outfit', sans-serif !important;
            }

            /* File Uploader styling */
            div[data-testid="stFileUploader"] {
                background-color: #FFFFFF !important;
                border: 1px dashed #CBD5E1 !important;
                border-radius: 10px !important;
                padding: 18px !important;
                transition: border-color 0.2s, background-color 0.2s;
            }
            div[data-testid="stFileUploader"]:hover {
                border-color: #4169A8 !important;
                background-color: #F8FAFC !important;
            }

            /* Dataframes & Tables */
            div[data-testid="stDataFrame"] {
                border: 1px solid #E2E8F0 !important;
                border-radius: 10px !important;
                background-color: #FFFFFF !important;
                overflow: hidden !important;
            }

            /* Alerts & Notification Banners */
            div[data-testid="stAlert"] {
                border-radius: 10px !important;
                padding: 14px 18px !important;
                font-size: 0.9rem !important;
            }

            /* Custom diagnostic card containers */
            .fs-card {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 16px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
            }
            .fs-card-highlight {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-left: 4px solid #4169A8;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 16px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
            }
            .fs-card-warn {
                background-color: #FDF8EE;
                border: 1px solid #EED8B4;
                border-left: 4px solid #A8752B;
                border-radius: 10px;
                padding: 18px;
                margin-bottom: 16px;
            }
            .fs-card-info {
                background-color: #EDF4F9;
                border: 1px solid #C8DFEF;
                border-left: 4px solid #477AA5;
                border-radius: 10px;
                padding: 18px;
                margin-bottom: 16px;
            }
            .fs-card-success {
                background-color: #EFF7F2;
                border: 1px solid #C6E2D3;
                border-left: 4px solid #3F7D62;
                border-radius: 10px;
                padding: 18px;
                margin-bottom: 16px;
            }

            /* Subsystem Status Panel in Sidebar */
            .fs-status-panel {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                padding: 12px 14px;
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
                color: #68778D;
                font-weight: 500;
            }
            .fs-status-icon {
                display: inline-flex;
                align-items: center;
                color: #68778D;
            }
            .fs-status-value {
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.75rem;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 6px;
                color: #243247;
            }

            /* Animated Pulse Indicators */
            @keyframes fs-pulse {
                0% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.35; transform: scale(0.85); }
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
                background-color: #A8752B;
                box-shadow: 0 0 4px rgba(168, 117, 43, 0.4);
            }
            .fs-pulse-dot-green {
                background-color: #3F7D62;
                box-shadow: 0 0 4px rgba(63, 125, 98, 0.4);
            }
            .fs-pulse-dot-red {
                background-color: #B84C4C;
                box-shadow: 0 0 4px rgba(184, 76, 76, 0.4);
            }

            /* Professional Safety Disclaimer Card */
            .fs-disclaimer-card {
                background-color: #FDF8EE;
                border: 1px solid #EED8B4;
                border-left: 3px solid #A8752B;
                border-radius: 10px;
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
                color: #A8752B;
            }
            .fs-disclaimer-title {
                font-size: 0.77rem;
                font-weight: 700;
                color: #7D561F;
                letter-spacing: 0.3px;
                text-transform: uppercase;
            }
            .fs-disclaimer-body {
                font-size: 0.77rem;
                line-height: 1.45;
                color: #634316;
                margin: 0;
            }

            /* Inline Icon Styling */
            .fs-icon {
                vertical-align: -0.22em;
            }

            /* Helper guidance cards */
            .fs-guide-step {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                padding: 16px;
                margin-bottom: 12px;
                box-shadow: 0 1px 2px rgba(0,0,0,0.02);
            }
            .fs-guide-step-title {
                font-size: 0.95rem;
                font-weight: 700;
                color: #243247;
                display: flex;
                align-items: center;
                gap: 8px;
                margin-bottom: 4px;
            }
            .fs-guide-step-desc {
                font-size: 0.84rem;
                color: #68778D;
                line-height: 1.4;
                margin: 0;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
