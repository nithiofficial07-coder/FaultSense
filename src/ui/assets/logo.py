"""Custom FaultSense branding assets including base64 SVG logo generators.

Industrial diagnostic aesthetic: elevator hoistway framing, dual vertical guide rails,
central intelligence diamond sensor, and precision cyan telemetry waveform.
"""

import base64


def get_faultsense_svg(
    width: int = 180,
    height: int = 44,
    show_text: bool = True,
    dark_mode: bool = True,
) -> str:
    """Returns a minified, single-line SVG string of the FaultSense brand logo."""
    text_color = "#F8FAFC" if dark_mode else "#0F172A"
    sub_color = "#06B6D4" if dark_mode else "#0891B2"

    text_group = ""
    if show_text:
        text_group = (
            f'<g transform="translate(46, 7)">'
            f'<text x="0" y="18" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif" font-size="16" font-weight="800" letter-spacing="1.2" fill="{text_color}">'
            f'FAULT<tspan fill="#06B6D4">SENSE</tspan>'
            f'</text>'
            f'<text x="0" y="30" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif" font-size="8.5" font-weight="600" letter-spacing="0.8" fill="{sub_color}">'
            f'ELEVATOR RCA ASSISTANT'
            f'</text>'
            f'</g>'
        )

    # Strictly single-line minified SVG (eliminates any markdown code-block indentation bugs)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
        f'<defs>'
        f'<linearGradient id="fs_cyan_glow" x1="0%" y1="0%" x2="100%" y2="100%">'
        f'<stop offset="0%" stop-color="#38BDF8" /><stop offset="50%" stop-color="#06B6D4" /><stop offset="100%" stop-color="#0284C7" />'
        f'</linearGradient>'
        f'<linearGradient id="fs_rail_grad" x1="0%" y1="0%" x2="0%" y2="100%">'
        f'<stop offset="0%" stop-color="#334155" /><stop offset="50%" stop-color="#64748B" /><stop offset="100%" stop-color="#334155" />'
        f'</linearGradient>'
        f'</defs>'
        f'<g transform="translate(4, 4)">'
        f'<line x1="6" y1="2" x2="6" y2="34" stroke="url(#fs_rail_grad)" stroke-width="2.5" stroke-linecap="round" />'
        f'<line x1="30" y1="2" x2="30" y2="34" stroke="url(#fs_rail_grad)" stroke-width="2.5" stroke-linecap="round" />'
        f'<line x1="3" y1="5" x2="33" y2="5" stroke="#1E293B" stroke-width="1.5" />'
        f'<line x1="3" y1="31" x2="33" y2="31" stroke="#1E293B" stroke-width="1.5" />'
        f'<rect x="9" y="8" width="18" height="20" rx="2.5" fill="#0F172A" stroke="#06B6D4" stroke-width="1.8" />'
        f'<line x1="18" y1="8" x2="18" y2="28" stroke="#1E293B" stroke-width="1.2" stroke-dasharray="2,1" />'
        f'<path d="M 4 18 L 12 18 L 15 13 L 18 23 L 21 15 L 24 18 L 32 18" fill="none" stroke="url(#fs_cyan_glow)" stroke-width="2.0" stroke-linecap="round" stroke-linejoin="round" />'
        f'<polygon points="18,14 21,18 18,22 15,18" fill="#38BDF8" stroke="#FFFFFF" stroke-width="0.8" />'
        f'</g>'
        f'{text_group}'
        f'</svg>'
    )
    return svg


def get_logo_data_uri(
    width: int = 180,
    height: int = 44,
    show_text: bool = True,
    dark_mode: bool = True,
) -> str:
    """Returns a base64 Data URI string for rendering SVG inside an img tag."""
    svg_str = get_faultsense_svg(width=width, height=height, show_text=show_text, dark_mode=dark_mode)
    b64 = base64.b64encode(svg_str.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def get_logo_html(
    width: int = 180,
    height: int = 44,
    show_text: bool = True,
    dark_mode: bool = True,
) -> str:
    """Returns an HTML img tag with base64 Data URI that never triggers markdown code blocks."""
    data_uri = get_logo_data_uri(width=width, height=height, show_text=show_text, dark_mode=dark_mode)
    return f'<img src="{data_uri}" width="{width}" height="{height}" style="display: inline-block; vertical-align: middle; border: none; max-width: 100%;" alt="FaultSense" />'
