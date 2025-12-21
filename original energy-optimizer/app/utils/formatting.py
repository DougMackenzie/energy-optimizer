"""
Formatting Utilities
Display formatting helpers
"""

from typing import Optional


def format_currency(value: float, decimals: int = 0, prefix: str = "$") -> str:
    """Format as currency"""
    if value >= 1e9:
        return f"{prefix}{value/1e9:.{decimals}f}B"
    elif value >= 1e6:
        return f"{prefix}{value/1e6:.{decimals}f}M"
    elif value >= 1e3:
        return f"{prefix}{value/1e3:.{decimals}f}K"
    else:
        return f"{prefix}{value:.{decimals}f}"


def format_power(mw: float, decimals: int = 1) -> str:
    """Format power in MW or GW"""
    if mw >= 1000:
        return f"{mw/1000:.{decimals}f} GW"
    else:
        return f"{mw:.{decimals}f} MW"


def format_energy(mwh: float, decimals: int = 1) -> str:
    """Format energy in MWh or GWh"""
    if mwh >= 1e6:
        return f"{mwh/1e6:.{decimals}f} TWh"
    elif mwh >= 1000:
        return f"{mwh/1000:.{decimals}f} GWh"
    else:
        return f"{mwh:.{decimals}f} MWh"


def format_time(months: int) -> str:
    """Format time in months or years"""
    if months >= 24:
        years = months / 12
        return f"{years:.1f} years"
    else:
        return f"{months} months"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format as percentage"""
    return f"{value:.{decimals}f}%"


def format_availability(availability: float) -> str:
    """Format availability with appropriate precision"""
    if availability >= 0.9999:
        return f"{availability * 100:.3f}%"
    elif availability >= 0.999:
        return f"{availability * 100:.2f}%"
    else:
        return f"{availability * 100:.1f}%"


def format_delta(value: float, unit: str = "", positive_prefix: str = "+") -> str:
    """Format a delta/change value"""
    prefix = positive_prefix if value > 0 else ""
    return f"{prefix}{value:.1f}{unit}"


def status_badge(status: str) -> str:
    """Return HTML for a status badge"""
    colors = {
        "complete": ("#d4edda", "#155724"),
        "success": ("#d4edda", "#155724"),
        "pass": ("#d4edda", "#155724"),
        "warning": ("#fff3cd", "#856404"),
        "warn": ("#fff3cd", "#856404"),
        "pending": ("#fff3cd", "#856404"),
        "danger": ("#f8d7da", "#721c24"),
        "fail": ("#f8d7da", "#721c24"),
        "error": ("#f8d7da", "#721c24"),
        "info": ("#d1ecf1", "#0c5460"),
        "needs_study": ("#cce5ff", "#004085"),
    }
    
    bg, text = colors.get(status.lower(), ("#e9ecef", "#495057"))
    
    return f"""
    <span style="
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 10px;
        font-weight: 600;
        background: {bg};
        color: {text};
    ">{status}</span>
    """


def metric_card_html(label: str, value: str, delta: Optional[str] = None, 
                     highlight_color: Optional[str] = None) -> str:
    """Generate HTML for a metric card"""
    border_style = f"border-left: 4px solid {highlight_color};" if highlight_color else ""
    delta_html = f'<div style="font-size: 10px; color: #666; margin-top: 2px;">{delta}</div>' if delta else ""
    
    return f"""
    <div style="
        background: white;
        border-radius: 6px;
        padding: 12px;
        border: 1px solid #e9ecef;
        {border_style}
    ">
        <div style="font-size: 9px; text-transform: uppercase; letter-spacing: 0.5px; color: #999; margin-bottom: 4px;">
            {label}
        </div>
        <div style="font-size: 20px; font-weight: 700; color: #1E3A5F; font-family: 'Roboto Mono', monospace;">
            {value}
        </div>
        {delta_html}
    </div>
    """
