"""Custom FaultSense branding assets including SVG logo and ReportLab Drawing generators.

Industrial diagnostic aesthetic: elevator hoistway framing, dual vertical guide rails,
central intelligence diamond sensor, and precision cyan telemetry waveform.
"""

from typing import Optional


def get_faultsense_svg(
    width: int = 180,
    height: int = 44,
    show_text: bool = True,
    dark_mode: bool = True,
) -> str:
    """Returns a standalone, scalable SVG string of the FaultSense brand logo."""
    text_color = "#F8FAFC" if dark_mode else "#0F172A"
    sub_color = "#06B6D4" if dark_mode else "#0891B2"

    text_group = ""
    if show_text:
        text_group = f"""
        <!-- Brand Typography -->
        <g transform="translate(48, 8)">
            <text x="0" y="18" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
                  font-size="16" font-weight="800" letter-spacing="1.2" fill="{text_color}">
                FAULT<tspan fill="#06B6D4">SENSE</tspan>
            </text>
            <text x="0" y="29" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
                  font-size="8.5" font-weight="600" letter-spacing="0.8" fill="{sub_color}">
                ELEVATOR DIAGNOSTICS
            </text>
        </g>
        """

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
    <defs>
        <linearGradient id="fs_cyan_glow" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#38BDF8" />
            <stop offset="50%" stop-color="#06B6D4" />
            <stop offset="100%" stop-color="#0284C7" />
        </linearGradient>
        <linearGradient id="fs_rail_grad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stop-color="#334155" />
            <stop offset="50%" stop-color="#64748B" />
            <stop offset="100%" stop-color="#334155" />
        </linearGradient>
        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="1.5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
    </defs>

    <!-- Logo Icon Group -->
    <g transform="translate(4, 4)">
        <!-- Hoistway Guide Rails (Left & Right) -->
        <line x1="6" y1="2" x2="6" y2="34" stroke="url(#fs_rail_grad)" stroke-width="2.5" stroke-linecap="round" />
        <line x1="30" y1="2" x2="30" y2="34" stroke="url(#fs_rail_grad)" stroke-width="2.5" stroke-linecap="round" />

        <!-- Top & Bottom Hoistway Structural Brackets -->
        <line x1="3" y1="5" x2="33" y2="5" stroke="#1E293B" stroke-width="1.5" />
        <line x1="3" y1="31" x2="33" y2="31" stroke="#1E293B" stroke-width="1.5" />

        <!-- Elevator Car Geometric Chassis -->
        <rect x="9" y="8" width="18" height="20" rx="2.5" fill="#0F172A" stroke="#06B6D4" stroke-width="1.8" />

        <!-- Car Door Divider -->
        <line x1="18" y1="8" x2="18" y2="28" stroke="#1E293B" stroke-width="1.2" stroke-dasharray="2,1" />

        <!-- Diagnostic Sensor Waveform Pulse -->
        <path d="M 4 18 L 12 18 L 15 13 L 18 23 L 21 15 L 24 18 L 32 18"
              fill="none" stroke="url(#fs_cyan_glow)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"
              filter="url(#glow)" />

        <!-- Central Intelligence Diamond Node -->
        <polygon points="18,14 21,18 18,22 15,18" fill="#38BDF8" stroke="#FFFFFF" stroke-width="0.8" />
    </g>

    {text_group}
</svg>"""
    return svg


def get_logo_html(
    width: int = 180,
    height: int = 44,
    show_text: bool = True,
    dark_mode: bool = True,
) -> str:
    """Returns an HTML-embeddable representation of the FaultSense SVG logo."""
    svg_content = get_faultsense_svg(
        width=width, height=height, show_text=show_text, dark_mode=dark_mode
    )
    return f'<div class="faultsense-logo" style="display:inline-flex; align-items:center;">{svg_content}</div>'
