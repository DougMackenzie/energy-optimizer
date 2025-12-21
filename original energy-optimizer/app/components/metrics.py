"""
Metrics Components
Metric cards and status displays
"""

import streamlit as st
from typing import List, Tuple, Optional


def metric_row(metrics: List[Tuple[str, str, Optional[str]]]):
    """
    Display a row of metrics
    
    Args:
        metrics: List of (label, value, delta) tuples
    """
    cols = st.columns(len(metrics))
    for i, (label, value, delta) in enumerate(metrics):
        with cols[i]:
            st.metric(label=label, value=value, delta=delta)


def metric_card(
    label: str,
    value: str,
    delta: Optional[str] = None,
    status: Optional[str] = None,
    highlight: bool = False,
):
    """
    Display a styled metric card
    
    Args:
        label: Metric label
        value: Metric value
        delta: Optional delta/subtitle
        status: Optional status color ("success", "warning", "danger")
        highlight: Whether to add accent highlight
    """
    colors = {
        "success": "#28A745",
        "warning": "#FFC107",
        "danger": "#DC3545",
        "primary": "#1E3A5F",
    }
    
    border_color = colors.get(status, "#F18F01" if highlight else "#dee2e6")
    value_color = colors.get(status, "#1E3A5F")
    
    html = f"""
    <div style="background: white; border-radius: 8px; padding: 12px 16px; 
                border: 1px solid #e9ecef; border-left: 4px solid {border_color};
                margin-bottom: 8px;">
        <div style="font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; 
                    color: #999; margin-bottom: 4px;">{label}</div>
        <div style="font-size: 20px; font-weight: 700; color: {value_color}; 
                    font-family: 'Roboto Mono', monospace;">{value}</div>
        {f'<div style="font-size: 11px; color: #666; margin-top: 2px;">{delta}</div>' if delta else ''}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def status_badge(
    text: str,
    status: str = "primary",
    size: str = "normal",
) -> str:
    """
    Return HTML for a status badge
    
    Args:
        text: Badge text
        status: "success", "warning", "danger", "info", "primary", "secondary"
        size: "small" or "normal"
    """
    colors = {
        "success": ("#d4edda", "#155724"),
        "warning": ("#fff3cd", "#856404"),
        "danger": ("#f8d7da", "#721c24"),
        "info": ("#d1ecf1", "#0c5460"),
        "primary": ("#cce5ff", "#004085"),
        "secondary": ("#e9ecef", "#495057"),
    }
    
    bg, fg = colors.get(status, colors["secondary"])
    font_size = "9px" if size == "small" else "11px"
    padding = "2px 6px" if size == "small" else "4px 8px"
    
    return f"""
    <span style="background: {bg}; color: {fg}; padding: {padding}; 
                 border-radius: 12px; font-size: {font_size}; font-weight: 600;">
        {text}
    </span>
    """


def progress_bar(
    value: float,
    max_value: float = 100,
    label: Optional[str] = None,
    color: str = "#2E86AB",
):
    """
    Display a progress bar
    
    Args:
        value: Current value
        max_value: Maximum value
        label: Optional label
        color: Bar color
    """
    pct = min(100, max(0, (value / max_value) * 100))
    
    html = f"""
    <div style="margin-bottom: 8px;">
        {f'<div style="font-size: 11px; margin-bottom: 4px;">{label}</div>' if label else ''}
        <div style="height: 8px; background: #e9ecef; border-radius: 4px; overflow: hidden;">
            <div style="width: {pct}%; height: 100%; background: {color};"></div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def constraint_status(
    name: str,
    current: float,
    limit: float,
    unit: str = "",
    is_max: bool = True,
):
    """
    Display constraint status with progress bar
    """
    if is_max:
        pct = (current / limit) * 100
        passed = current <= limit
    else:
        pct = (limit / current) * 100 if current > 0 else 0
        passed = current >= limit
    
    color = "#28A745" if passed else "#DC3545"
    status_text = "✓ Pass" if passed else "✗ Fail"
    
    html = f"""
    <div style="display: flex; align-items: center; margin-bottom: 8px;">
        <div style="width: 120px; font-size: 11px;">{name}</div>
        <div style="flex: 1; height: 18px; background: #f8f9fa; border-radius: 3px; 
                    overflow: hidden; margin: 0 10px;">
            <div style="width: {min(100, pct)}%; height: 100%; background: {color}; opacity: 0.7;"></div>
        </div>
        <div style="width: 80px; font-size: 10px; font-family: monospace;">
            {current:.1f} / {limit:.1f} {unit}
        </div>
        <div style="width: 50px; font-size: 10px; color: {color}; font-weight: 600;">
            {status_text}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
