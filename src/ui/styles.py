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
                --fs-bg-sidebar: #F5F8FD;
                --fs-bg-card: #FFFFFF;
                --fs-text-primary: #27364B;
                --fs-text-secondary: #64748B;
                --fs-accent-primary: #4169A8;
                --fs-accent-hover: #34558B;
                --fs-accent-subtle: #EAF1FA;
                --fs-border-subtle: #DCE5F1;
                --fs-bg-hover: #EFF4FB;
                --fs-nav-active: #E6EEFA;
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
                background-color: #F5F8FD !important;
                border-right: 1px solid #DCE5F1 !important;
            }
            section[data-testid="stSidebar"] > div,
            section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {
                padding-top: 0.85rem !important;
                padding-bottom: 1.5rem !important;
                padding-left: 0.85rem !important;
                padding-right: 0.85rem !important;
                background-color: #F5F8FD !important;
            }

            /* Sidebar compact vertical spacing with guaranteed clearance */
            section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"],
            section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div[data-testid="element-container"],
            section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div.stElementContainer {
                margin-bottom: 0 !important;
                min-height: auto !important;
                overflow: visible !important;
            }
            section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
                gap: 0.3rem !important;
            }

            /* Cancel Streamlit default negative bottom margin on markdown containers in sidebar */
            section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"],
            section[data-testid="stSidebar"] div.stMarkdownContainer,
            section[data-testid="stSidebar"] div[data-testid="stMarkdown"] {
                margin-bottom: 0 !important;
            }

            /* Navigation headings guaranteed clearance and alignment */
            section[data-testid="stSidebar"] div[data-testid="stElementContainer"]:has(.fs-nav-heading),
            section[data-testid="stSidebar"] div.stElementContainer:has(.fs-nav-heading),
            section[data-testid="stSidebar"] div[data-testid="element-container"]:has(.fs-nav-heading) {
                margin-top: 10px !important;
                margin-bottom: 6px !important;
                min-height: 24px !important;
                display: block !important;
                overflow: visible !important;
            }

            .fs-nav-heading {
                display: block !important;
                width: 100% !important;
                font-size: 0.72rem !important;
                text-transform: uppercase !important;
                font-weight: 700 !important;
                color: #64748B !important;
                letter-spacing: 0.08em !important;
                padding: 4px 14px 2px 14px !important;
                margin: 0 0 4px 0 !important;
                line-height: 1.4 !important;
                box-sizing: border-box !important;
                clear: both !important;
            }

            /* Button spacing within sidebar */
            section[data-testid="stSidebar"] div[data-testid="stButton"] {
                margin-bottom: 7px !important;
                margin-top: 0 !important;
            }

            /* Explicit cursor: pointer on sidebar navigation buttons and all child nodes */
            section[data-testid="stSidebar"] div[data-testid="stButton"],
            section[data-testid="stSidebar"] div[data-testid="stButton"] button,
            section[data-testid="stSidebar"] div[data-testid="stButton"] * {
                cursor: pointer !important;
            }

            /* Professional entrance micro-animation for sidebar navigation items */
            @keyframes fs-nav-item-enter {
                0% {
                    opacity: 0.6;
                    transform: translateY(3px);
                }
                100% {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            /* Sidebar navigation button item styling (standard 46px height, precision left-aligned) */
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
                width: 100% !important;
                min-height: 46px !important;
                height: 46px !important;
                max-height: 46px !important;
                display: flex !important;
                flex-direction: row !important;
                align-items: center !important;
                justify-content: flex-start !important;
                text-align: left !important;
                padding: 0 14px !important;
                margin: 0 !important;
                box-sizing: border-box !important;
                background-color: #FFFFFF !important;
                border: 1px solid #DCE5F1 !important;
                border-radius: 10px !important;
                color: #27364B !important;
                font-weight: 500 !important;
                font-size: 0.88rem !important;
                box-shadow: 0 1px 2px rgba(36, 50, 71, 0.03) !important;
                transition: all 180ms cubic-bezier(0.16, 1, 0.3, 1) !important;
                position: relative !important;
                overflow: hidden !important;
                cursor: pointer !important;
                animation: fs-nav-item-enter 0.22s cubic-bezier(0.16, 1, 0.3, 1) both;
            }

            /* Subtle animated pointer highlight on hover */
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button::before {
                content: '' !important;
                position: absolute !important;
                left: 0 !important;
                top: 50% !important;
                height: 0% !important;
                width: 3px !important;
                background: #8BADE8 !important;
                border-radius: 0 3px 3px 0 !important;
                opacity: 0 !important;
                transition: all 180ms cubic-bezier(0.16, 1, 0.3, 1) !important;
            }

            /* Navigation button hover state with smooth micro-interaction */
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
                background-color: #EFF4FB !important;
                border-color: #CBDDF5 !important;
                color: #4169A8 !important;
                transform: translateX(2px) !important;
                box-shadow: 0 2px 6px rgba(65, 105, 168, 0.08) !important;
            }

            section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover::before {
                opacity: 1 !important;
                height: 65% !important;
                top: 17.5% !important;
            }

            section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover span[data-testid="stIconMaterial"],
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover span.material-symbols-rounded {
                color: #4169A8 !important;
                transform: scale(1.08) !important;
                transition: transform 180ms cubic-bezier(0.16, 1, 0.3, 1), color 180ms ease !important;
            }

            /* Active navigation item styling with gentle breathing glow */
            @keyframes fs-active-pulse {
                0%, 100% {
                    box-shadow: 0 1px 3px rgba(65, 105, 168, 0.1);
                }
                50% {
                    box-shadow: 0 2px 7px rgba(65, 105, 168, 0.2);
                }
            }

            section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"],
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"] {
                background-color: #E6EEFA !important;
                border: 1px solid #C4D7F0 !important;
                color: #27364B !important;
                font-weight: 600 !important;
                animation: fs-active-pulse 3.5s ease-in-out infinite !important;
                transform: none !important;
                padding: 0 14px !important;
            }

            /* Active item left accent indicator (4px width) */
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"]::before,
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"]::before {
                content: '' !important;
                position: absolute !important;
                left: 0 !important;
                top: 0 !important;
                height: 100% !important;
                width: 4px !important;
                background: #4169A8 !important;
                border-radius: 10px 0 0 10px !important;
                opacity: 1 !important;
                display: block !important;
            }

            section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"]:hover,
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"]:hover {
                background-color: #DEE9F8 !important;
                border-color: #B8D2F4 !important;
                color: #27364B !important;
                transform: none !important;
            }

            section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] span[data-testid="stIconMaterial"],
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"] span[data-testid="stIconMaterial"],
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] span.material-symbols-rounded,
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"] span.material-symbols-rounded {
                color: #4169A8 !important;
                font-weight: 600 !important;
            }

            /* Internal layout: flex alignment for Streamlit markdown container & paragraph */
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button > div {
                width: 100% !important;
                display: flex !important;
                flex-direction: row !important;
                align-items: center !important;
                justify-content: flex-start !important;
                text-align: left !important;
                padding: 0 !important;
                margin: 0 !important;
                overflow: visible !important;
            }

            section[data-testid="stSidebar"] div[data-testid="stButton"] > button div[data-testid="stMarkdownContainer"] {
                width: 100% !important;
                display: flex !important;
                flex-direction: row !important;
                align-items: center !important;
                justify-content: flex-start !important;
                text-align: left !important;
                padding: 0 !important;
                margin: 0 !important;
                overflow: hidden !important;
            }

            section[data-testid="stSidebar"] div[data-testid="stButton"] > button p {
                display: flex !important;
                flex-direction: row !important;
                align-items: center !important;
                justify-content: flex-start !important;
                text-align: left !important;
                width: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
                font-size: 0.88rem !important;
                font-weight: inherit !important;
                color: inherit !important;
                line-height: 1.25 !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
            }

            /* Icon wrapper span: dedicated 20px column with 10px spacing to text */
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button span:has(> [data-testid="stIconMaterial"]),
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button span[class*="e1fmktau2"],
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button span.st-emotion-cache-28gi3v {
                display: inline-flex !important;
                align-items: center !important;
                justify-content: center !important;
                width: 20px !important;
                min-width: 20px !important;
                max-width: 20px !important;
                height: 20px !important;
                margin: 0 10px 0 0 !important;
                padding: 0 !important;
                flex-shrink: 0 !important;
                overflow: visible !important;
            }

            /* Material icon glyph: centered inside 20px wrapper without negative offsets or clipping */
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button span[data-testid="stIconMaterial"],
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button span.material-symbols-rounded {
                display: inline-flex !important;
                align-items: center !important;
                justify-content: center !important;
                text-align: center !important;
                width: 100% !important;
                height: 100% !important;
                font-size: 19px !important;
                line-height: 1 !important;
                margin: 0 !important;
                padding: 0 !important;
                flex-shrink: 0 !important;
                color: #64748B !important;
                transition: color 160ms ease !important;
                vertical-align: middle !important;
                overflow: visible !important;
            }

            /* Quick-action 3-column buttons in active session card */
            section[data-testid="stSidebar"] div[data-testid="column"] div[data-testid="stButton"] > button {
                height: 32px !important;
                min-height: 32px !important;
                max-height: 32px !important;
                padding: 0 6px !important;
                font-size: 0.78rem !important;
                justify-content: center !important;
                text-align: center !important;
                border-radius: 6px !important;
                transform: none !important;
            }
            section[data-testid="stSidebar"] div[data-testid="column"] div[data-testid="stButton"] > button::before {
                display: none !important;
            }
            section[data-testid="stSidebar"] div[data-testid="column"] div[data-testid="stButton"] > button span[data-testid="stIconMaterial"],
            section[data-testid="stSidebar"] div[data-testid="column"] div[data-testid="stButton"] > button span.material-symbols-rounded {
                font-size: 14px !important;
                width: 14px !important;
                min-width: 14px !important;
                margin-right: 4px !important;
            }

            /* Refined Cursor Indicator (matching Screenshot 2: soft translucent blue lens on hover) */
            #fs-global-cursor,
            #fs-sidebar-pointer {
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                width: 16px !important;
                height: 16px !important;
                border-radius: 50% !important;
                background: rgba(139, 173, 232, 0.28) !important;
                border: 1.5px solid #8BADE8 !important;
                pointer-events: none !important;
                z-index: 999999 !important;
                opacity: 0;
                transform: translate(-50%, -50%) scale(0.7);
                transition: opacity 0.18s ease, transform 0.18s cubic-bezier(0.16, 1, 0.3, 1), background-color 0.15s ease, border-color 0.15s ease;
                box-shadow: 0 0 6px rgba(139, 173, 232, 0.35) !important;
                will-change: left, top, transform;
            }

            #fs-global-cursor.fs-cursor-visible,
            #fs-sidebar-pointer.fs-pointer-visible {
                opacity: 1 !important;
                transform: translate(-50%, -50%) scale(1) !important;
            }

            #fs-global-cursor.fs-cursor-hover,
            #fs-sidebar-pointer.fs-pointer-hover {
                transform: translate(-50%, -50%) scale(1.18) !important;
                border-color: #719BE0 !important;
                background: rgba(139, 173, 232, 0.42) !important;
                box-shadow: 0 0 8px rgba(139, 173, 232, 0.45) !important;
            }

            @media (prefers-reduced-motion: reduce) {
                #fs-global-cursor,
                #fs-sidebar-pointer {
                    display: none !important;
                }
                section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
                    transition: none !important;
                }
                section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
                    transform: none !important;
                }
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
                background-color: #FFFFFF;
                border: 1px solid #DCE5F1;
                border-radius: 10px;
                padding: 10px 14px;
                margin-bottom: 12px;
                box-shadow: 0 1px 2px rgba(36, 50, 71, 0.03);
            }
            .fs-status-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 7px 0;
                font-size: 0.78rem;
                border-bottom: 1px solid #DCE5F1;
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
