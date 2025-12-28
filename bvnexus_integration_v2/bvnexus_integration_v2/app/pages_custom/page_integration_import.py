"""
bvNexus Integration Import Page (Enhanced)
==========================================

Enhanced import page with:
- Sample result file previews
- Visual validation dashboards
- Constraint feedback visualization
- Project progress tracking
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import io

# =============================================================================
# DATA MODELS
# =============================================================================

class ValidationStatus(Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    NOT_RUN = "not_run"


@dataclass
class ValidationResult:
    """Result from external validation tool."""
    result_id: str
    tool: str
    study_type: str
    timestamp: datetime
    status: ValidationStatus
    metrics: Dict[str, float] = field(default_factory=dict)
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    source_file: str = ""


@dataclass
class ConstraintUpdate:
    """Suggested constraint update based on validation results."""
    constraint_name: str
    current_value: float
    suggested_value: float
    reason: str
    source_study: str
    priority: str
    impact: str = ""


# =============================================================================
# VALIDATION CRITERIA
# =============================================================================

VALIDATION_CRITERIA = {
    'etap_loadflow': {
        'voltage_pu_min': {'min': 0.95, 'max': 1.05, 'unit': 'pu', 'name': 'Minimum Voltage'},
        'voltage_pu_max': {'min': 0.95, 'max': 1.05, 'unit': 'pu', 'name': 'Maximum Voltage'},
        'loading_pct': {'min': 0, 'max': 80, 'unit': '%', 'name': 'Equipment Loading'},
    },
    'etap_shortcircuit': {
        'fault_current_ka': {'min': 0, 'max': 50, 'unit': 'kA', 'name': 'Fault Current'},
        'breaker_duty_pct': {'min': 0, 'max': 100, 'unit': '%', 'name': 'Breaker Duty'},
    },
    'psse_powerflow': {
        'voltage_pu': {'min': 0.95, 'max': 1.05, 'unit': 'pu', 'name': 'Bus Voltage'},
        'angle_deg': {'min': -30, 'max': 30, 'unit': 'deg', 'name': 'Voltage Angle'},
    },
    'ram_availability': {
        'system_availability': {'min': 0.9995, 'max': 1.0, 'unit': '', 'name': 'System Availability'},
        'annual_downtime_hrs': {'min': 0, 'max': 4.38, 'unit': 'hrs', 'name': 'Annual Downtime'},
    },
}


# =============================================================================
# SAMPLE RESULT GENERATORS (for demonstration)
# =============================================================================

def generate_sample_etap_lf_results(pass_fail: str = "pass") -> pd.DataFrame:
    """Generate sample ETAP load flow results."""
    if pass_fail == "pass":
        return pd.DataFrame([
            {'Bus_ID': 'BUS_100', 'Bus_Name': 'RECIP_1_BUS', 'Voltage_kV': 13.8, 'Voltage_pu': 1.012, 
             'Angle_deg': 2.3, 'P_MW': 18.3, 'Q_MVAR': 9.8, 'Loading_pct': 72.5},
            {'Bus_ID': 'BUS_101', 'Bus_Name': 'RECIP_2_BUS', 'Voltage_kV': 13.8, 'Voltage_pu': 1.008, 
             'Angle_deg': 2.1, 'P_MW': 18.3, 'Q_MVAR': 9.6, 'Loading_pct': 71.8},
            {'Bus_ID': 'BUS_120', 'Bus_Name': 'GT_1_BUS', 'Voltage_kV': 13.8, 'Voltage_pu': 1.025, 
             'Angle_deg': 0.0, 'P_MW': 50.0, 'Q_MVAR': 25.0, 'Loading_pct': 78.0},
            {'Bus_ID': 'BUS_200', 'Bus_Name': 'MAIN_BUS', 'Voltage_kV': 13.8, 'Voltage_pu': 1.000, 
             'Angle_deg': 0.0, 'P_MW': -200.0, 'Q_MVAR': -65.0, 'Loading_pct': 75.2},
        ])
    else:  # fail
        return pd.DataFrame([
            {'Bus_ID': 'BUS_100', 'Bus_Name': 'RECIP_1_BUS', 'Voltage_kV': 13.8, 'Voltage_pu': 0.932, 
             'Angle_deg': 5.8, 'P_MW': 18.3, 'Q_MVAR': 12.5, 'Loading_pct': 92.5},
            {'Bus_ID': 'BUS_101', 'Bus_Name': 'RECIP_2_BUS', 'Voltage_kV': 13.8, 'Voltage_pu': 0.928, 
             'Angle_deg': 5.5, 'P_MW': 18.3, 'Q_MVAR': 12.2, 'Loading_pct': 95.8},
            {'Bus_ID': 'BUS_120', 'Bus_Name': 'GT_1_BUS', 'Voltage_kV': 13.8, 'Voltage_pu': 1.025, 
             'Angle_deg': 0.0, 'P_MW': 50.0, 'Q_MVAR': 30.0, 'Loading_pct': 105.0},
            {'Bus_ID': 'BUS_200', 'Bus_Name': 'MAIN_BUS', 'Voltage_kV': 13.8, 'Voltage_pu': 0.945, 
             'Angle_deg': 0.0, 'P_MW': -200.0, 'Q_MVAR': -85.0, 'Loading_pct': 98.2},
        ])


def generate_sample_etap_sc_results(pass_fail: str = "pass") -> pd.DataFrame:
    """Generate sample ETAP short circuit results."""
    if pass_fail == "pass":
        return pd.DataFrame([
            {'Bus_ID': 'BUS_100', 'Bus_Name': 'RECIP_1_BUS', 'Fault_Type': '3-Phase', 
             'Isc_kA': 28.5, 'X_R_Ratio': 12.5, 'Breaker_Rating_kA': 40.0, 'Duty_pct': 71.3},
            {'Bus_ID': 'BUS_120', 'Bus_Name': 'GT_1_BUS', 'Fault_Type': '3-Phase', 
             'Isc_kA': 35.2, 'X_R_Ratio': 15.8, 'Breaker_Rating_kA': 50.0, 'Duty_pct': 70.4},
            {'Bus_ID': 'BUS_200', 'Bus_Name': 'MAIN_BUS', 'Fault_Type': '3-Phase', 
             'Isc_kA': 42.8, 'X_R_Ratio': 18.2, 'Breaker_Rating_kA': 63.0, 'Duty_pct': 67.9},
        ])
    else:
        return pd.DataFrame([
            {'Bus_ID': 'BUS_100', 'Bus_Name': 'RECIP_1_BUS', 'Fault_Type': '3-Phase', 
             'Isc_kA': 45.5, 'X_R_Ratio': 22.5, 'Breaker_Rating_kA': 40.0, 'Duty_pct': 113.8},
            {'Bus_ID': 'BUS_120', 'Bus_Name': 'GT_1_BUS', 'Fault_Type': '3-Phase', 
             'Isc_kA': 52.2, 'X_R_Ratio': 25.8, 'Breaker_Rating_kA': 50.0, 'Duty_pct': 104.4},
            {'Bus_ID': 'BUS_200', 'Bus_Name': 'MAIN_BUS', 'Fault_Type': '3-Phase', 
             'Isc_kA': 58.8, 'X_R_Ratio': 28.2, 'Breaker_Rating_kA': 63.0, 'Duty_pct': 93.3},
        ])


def generate_sample_psse_results(pass_fail: str = "pass") -> pd.DataFrame:
    """Generate sample PSS/e results."""
    if pass_fail == "pass":
        return pd.DataFrame([
            {'BUS': 100, 'NAME': 'RECIP_01', 'VM_PU': 1.010, 'VA_DEG': 2.3, 'P_GEN_MW': 18.3, 'Q_GEN_MVAR': 9.8},
            {'BUS': 120, 'NAME': 'GT_01', 'VM_PU': 1.025, 'VA_DEG': 0.0, 'P_GEN_MW': 50.0, 'Q_GEN_MVAR': 25.0},
            {'BUS': 200, 'NAME': 'MAIN_BUS', 'VM_PU': 1.000, 'VA_DEG': 0.0, 'P_GEN_MW': 0.0, 'Q_GEN_MVAR': 0.0},
        ])
    else:
        return pd.DataFrame([
            {'BUS': 100, 'NAME': 'RECIP_01', 'VM_PU': 0.915, 'VA_DEG': 12.3, 'P_GEN_MW': 18.3, 'Q_GEN_MVAR': 15.8},
            {'BUS': 120, 'NAME': 'GT_01', 'VM_PU': 1.085, 'VA_DEG': -5.0, 'P_GEN_MW': 50.0, 'Q_GEN_MVAR': 35.0},
            {'BUS': 200, 'NAME': 'MAIN_BUS', 'VM_PU': 0.938, 'VA_DEG': 0.0, 'P_GEN_MW': 0.0, 'Q_GEN_MVAR': 0.0},
        ])


def generate_sample_ram_results(pass_fail: str = "pass") -> pd.DataFrame:
    """Generate sample Windchill RAM results."""
    if pass_fail == "pass":
        return pd.DataFrame([
            {'Block_ID': 'THERMAL_GEN', 'Block_Name': 'Thermal Generation', 
             'Availability': 0.99987, 'MTBF_Hours': 76923, 'MTTR_Hours': 10, 'Annual_Downtime_Hours': 1.14},
            {'Block_ID': 'ELECTRICAL', 'Block_Name': 'Electrical Distribution', 
             'Availability': 0.99985, 'MTBF_Hours': 67308, 'MTTR_Hours': 10, 'Annual_Downtime_Hours': 1.31},
            {'Block_ID': 'SYSTEM', 'Block_Name': 'Complete System', 
             'Availability': 0.99972, 'MTBF_Hours': 35714, 'MTTR_Hours': 10, 'Annual_Downtime_Hours': 2.45},
        ])
    else:
        return pd.DataFrame([
            {'Block_ID': 'THERMAL_GEN', 'Block_Name': 'Thermal Generation', 
             'Availability': 0.99850, 'MTBF_Hours': 6667, 'MTTR_Hours': 10, 'Annual_Downtime_Hours': 13.14},
            {'Block_ID': 'ELECTRICAL', 'Block_Name': 'Electrical Distribution', 
             'Availability': 0.99870, 'MTBF_Hours': 67308, 'MTTR_Hours': 88, 'Annual_Downtime_Hours': 11.39},
            {'Block_ID': 'SYSTEM', 'Block_Name': 'Complete System', 
             'Availability': 0.99720, 'MTBF_Hours': 3125, 'MTTR_Hours': 88, 'Annual_Downtime_Hours': 24.53},
        ])


# =============================================================================
# RESULT PARSERS
# =============================================================================

def parse_etap_loadflow(df: pd.DataFrame) -> ValidationResult:
    """Parse ETAP load flow results."""
    result = ValidationResult(
        result_id=f"ETAP_LF_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        tool="ETAP",
        study_type="Load Flow",
        timestamp=datetime.now(),
        status=ValidationStatus.PENDING,
    )
    
    criteria = VALIDATION_CRITERIA['etap_loadflow']
    violations = []
    warnings = []
    metrics = {}
    
    # Find voltage column
    v_cols = [c for c in df.columns if 'voltage' in c.lower() and 'pu' in c.lower()]
    if not v_cols:
        v_cols = [c for c in df.columns if 'pu' in c.lower()]
    
    if v_cols:
        voltages = pd.to_numeric(df[v_cols[0]], errors='coerce').dropna()
        if len(voltages) > 0:
            v_min, v_max = voltages.min(), voltages.max()
            metrics['voltage_pu_min'] = v_min
            metrics['voltage_pu_max'] = v_max
            
            if v_min < criteria['voltage_pu_min']['min']:
                violations.append(f"Under-voltage: {v_min:.4f} pu < 0.95 pu limit")
            if v_max > criteria['voltage_pu_max']['max']:
                violations.append(f"Over-voltage: {v_max:.4f} pu > 1.05 pu limit")
    
    # Find loading column
    l_cols = [c for c in df.columns if 'loading' in c.lower() or 'load' in c.lower() and '%' in c.lower()]
    if not l_cols:
        l_cols = [c for c in df.columns if 'pct' in c.lower()]
    
    if l_cols:
        loadings = pd.to_numeric(df[l_cols[0]], errors='coerce').dropna()
        if len(loadings) > 0:
            l_max = loadings.max()
            metrics['loading_pct_max'] = l_max
            
            if l_max > 100:
                violations.append(f"Overloaded equipment: {l_max:.1f}% > 100%")
            elif l_max > 80:
                warnings.append(f"High loading: {l_max:.1f}% > 80% recommended")
    
    # Set status
    if violations:
        result.status = ValidationStatus.FAILED
        result.recommendations.append("Review equipment sizing and consider adding capacity")
    elif warnings:
        result.status = ValidationStatus.WARNING
        result.recommendations.append("Monitor high-load equipment during peak periods")
    else:
        result.status = ValidationStatus.PASSED
    
    result.metrics = metrics
    result.violations = violations
    result.warnings = warnings
    
    return result


def parse_etap_shortcircuit(df: pd.DataFrame) -> ValidationResult:
    """Parse ETAP short circuit results."""
    result = ValidationResult(
        result_id=f"ETAP_SC_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        tool="ETAP",
        study_type="Short Circuit",
        timestamp=datetime.now(),
        status=ValidationStatus.PENDING,
    )
    
    violations = []
    warnings = []
    metrics = {}
    
    # Find duty column
    duty_cols = [c for c in df.columns if 'duty' in c.lower() or 'rating' in c.lower()]
    
    if duty_cols:
        duties = pd.to_numeric(df[duty_cols[0]], errors='coerce').dropna()
        if len(duties) > 0:
            d_max = duties.max()
            metrics['breaker_duty_max_pct'] = d_max
            
            if d_max > 100:
                violations.append(f"Breaker duty exceeded: {d_max:.1f}% > 100%")
            elif d_max > 80:
                warnings.append(f"High breaker duty: {d_max:.1f}%")
    
    # Find fault current column
    isc_cols = [c for c in df.columns if 'isc' in c.lower() or 'fault' in c.lower()]
    
    if isc_cols:
        faults = pd.to_numeric(df[isc_cols[0]], errors='coerce').dropna()
        if len(faults) > 0:
            f_max = faults.max()
            metrics['fault_current_max_ka'] = f_max
    
    if violations:
        result.status = ValidationStatus.FAILED
        result.recommendations.append("Upgrade breakers or add current-limiting reactors")
    elif warnings:
        result.status = ValidationStatus.WARNING
    else:
        result.status = ValidationStatus.PASSED
    
    result.metrics = metrics
    result.violations = violations
    result.warnings = warnings
    
    return result


def parse_psse_results(df: pd.DataFrame) -> ValidationResult:
    """Parse PSS/e power flow results."""
    result = ValidationResult(
        result_id=f"PSSE_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        tool="PSS/e",
        study_type="Power Flow",
        timestamp=datetime.now(),
        status=ValidationStatus.PENDING,
    )
    
    violations = []
    warnings = []
    metrics = {}
    
    # Find voltage column
    v_cols = [c for c in df.columns if 'vm' in c.lower() or 'voltage' in c.lower()]
    
    if v_cols:
        voltages = pd.to_numeric(df[v_cols[0]], errors='coerce').dropna()
        if len(voltages) > 0:
            v_min, v_max = voltages.min(), voltages.max()
            metrics['voltage_pu_min'] = v_min
            metrics['voltage_pu_max'] = v_max
            
            if v_min < 0.95:
                violations.append(f"Under-voltage: {v_min:.4f} pu")
            if v_max > 1.05:
                violations.append(f"Over-voltage: {v_max:.4f} pu")
    
    # Find angle column
    a_cols = [c for c in df.columns if 'va' in c.lower() or 'angle' in c.lower()]
    
    if a_cols:
        angles = pd.to_numeric(df[a_cols[0]], errors='coerce').dropna()
        if len(angles) > 0:
            a_max = abs(angles).max()
            metrics['angle_max_deg'] = a_max
            
            if a_max > 30:
                warnings.append(f"Large angle separation: {a_max:.1f}°")
    
    if violations:
        result.status = ValidationStatus.FAILED
    elif warnings:
        result.status = ValidationStatus.WARNING
    else:
        result.status = ValidationStatus.PASSED
    
    result.metrics = metrics
    result.violations = violations
    result.warnings = warnings
    
    return result


def parse_ram_results(df: pd.DataFrame) -> ValidationResult:
    """Parse Windchill RAM results."""
    result = ValidationResult(
        result_id=f"RAM_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        tool="Windchill RAM",
        study_type="Availability Analysis",
        timestamp=datetime.now(),
        status=ValidationStatus.PENDING,
    )
    
    criteria = VALIDATION_CRITERIA['ram_availability']
    violations = []
    warnings = []
    metrics = {}
    
    # Find system row
    system_rows = df[df['Block_ID'].str.contains('SYSTEM', case=False, na=False)]
    if len(system_rows) == 0:
        system_rows = df.tail(1)  # Assume last row is system
    
    if len(system_rows) > 0:
        row = system_rows.iloc[0]
        
        # Get availability
        avail_cols = [c for c in df.columns if 'avail' in c.lower()]
        if avail_cols:
            avail = float(row[avail_cols[0]])
            if avail > 1:
                avail = avail / 100  # Convert from percentage
            metrics['system_availability'] = avail
            
            if avail < criteria['system_availability']['min']:
                violations.append(
                    f"System availability {avail*100:.3f}% < {criteria['system_availability']['min']*100:.2f}% target"
                )
        
        # Get downtime
        dt_cols = [c for c in df.columns if 'downtime' in c.lower()]
        if dt_cols:
            downtime = float(row[dt_cols[0]])
            metrics['annual_downtime_hrs'] = downtime
            
            if downtime > criteria['annual_downtime_hrs']['max']:
                violations.append(
                    f"Annual downtime {downtime:.2f} hrs > {criteria['annual_downtime_hrs']['max']:.2f} hrs target"
                )
    
    if violations:
        result.status = ValidationStatus.FAILED
        result.recommendations.append("Increase redundancy or reduce MTTR through spare parts inventory")
    else:
        result.status = ValidationStatus.PASSED
    
    result.metrics = metrics
    result.violations = violations
    result.warnings = warnings
    
    return result


def generate_constraint_updates(result: ValidationResult) -> List[ConstraintUpdate]:
    """Generate constraint updates based on validation result."""
    updates = []
    
    if result.status == ValidationStatus.FAILED:
        if result.tool == "Windchill RAM":
            if 'system_availability' in result.metrics:
                current = result.metrics['system_availability']
                target = 0.9995
                if current < target:
                    updates.append(ConstraintUpdate(
                        constraint_name='redundancy_level',
                        current_value=1,
                        suggested_value=2,
                        reason=f"Availability {current*100:.2f}% below {target*100:.2f}% target",
                        source_study=result.result_id,
                        priority='Critical',
                        impact='Add one additional generator unit for N+2 redundancy',
                    ))
        
        elif result.tool == "ETAP" and result.study_type == "Load Flow":
            if 'voltage_pu_min' in result.metrics:
                v_min = result.metrics['voltage_pu_min']
                if v_min < 0.95:
                    updates.append(ConstraintUpdate(
                        constraint_name='reactive_support_mvar',
                        current_value=0,
                        suggested_value=20,
                        reason=f"Voltage {v_min:.4f} pu below 0.95 pu limit",
                        source_study=result.result_id,
                        priority='High',
                        impact='Add capacitor bank or adjust generator AVR settings',
                    ))
        
        elif result.tool == "ETAP" and result.study_type == "Short Circuit":
            if 'breaker_duty_max_pct' in result.metrics:
                duty = result.metrics['breaker_duty_max_pct']
                if duty > 100:
                    updates.append(ConstraintUpdate(
                        constraint_name='breaker_rating_ka',
                        current_value=40,
                        suggested_value=63,
                        reason=f"Breaker duty {duty:.1f}% exceeds rating",
                        source_study=result.result_id,
                        priority='Critical',
                        impact='Upgrade main switchgear breakers',
                    ))
    
    return updates


# =============================================================================
# VISUALIZATION FUNCTIONS
# =============================================================================

def create_validation_gauge_svg(value: float, target: float, label: str, unit: str = "") -> str:
    """Create a gauge visualization for validation metrics."""
    # Normalize to 0-180 degrees
    pct = min(value / target, 1.5) if target > 0 else 0
    angle = 180 - (pct * 180)
    
    # Determine color
    if pct >= 1.0:
        color = "#4CAF50"  # Green
        status = "PASS"
    elif pct >= 0.95:
        color = "#FFC107"  # Yellow
        status = "WARN"
    else:
        color = "#f44336"  # Red
        status = "FAIL"
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 120">
        <style>
            .gauge-bg {{ fill: none; stroke: #e0e0e0; stroke-width: 15; }}
            .gauge-fill {{ fill: none; stroke: {color}; stroke-width: 15; stroke-linecap: round; }}
            .gauge-text {{ font-family: Arial; font-size: 14px; fill: #333; }}
            .gauge-value {{ font-family: Arial; font-size: 24px; font-weight: bold; fill: {color}; }}
            .gauge-label {{ font-family: Arial; font-size: 12px; fill: #666; }}
        </style>
        
        <!-- Background arc -->
        <path d="M 20 100 A 80 80 0 0 1 180 100" class="gauge-bg"/>
        
        <!-- Filled arc -->
        <path d="M 20 100 A 80 80 0 0 1 180 100" class="gauge-fill"
              stroke-dasharray="{pct * 251}" stroke-dashoffset="0"/>
        
        <!-- Center value -->
        <text x="100" y="85" class="gauge-value" text-anchor="middle">{value:.2f}{unit}</text>
        <text x="100" y="105" class="gauge-label" text-anchor="middle">{label}</text>
        <text x="100" y="118" class="gauge-text" text-anchor="middle" fill="{color}">{status}</text>
        
        <!-- Target marker -->
        <text x="175" y="105" class="gauge-label" text-anchor="middle">Target: {target:.2f}</text>
    </svg>'''
    
    return svg


def create_status_card_html(title: str, status: ValidationStatus, metrics: Dict) -> str:
    """Create an HTML card for validation status."""
    colors = {
        ValidationStatus.PASSED: ("#4CAF50", "✅"),
        ValidationStatus.FAILED: ("#f44336", "❌"),
        ValidationStatus.WARNING: ("#FFC107", "⚠️"),
        ValidationStatus.PENDING: ("#9e9e9e", "⏳"),
        ValidationStatus.NOT_RUN: ("#9e9e9e", "➖"),
    }
    
    color, icon = colors.get(status, ("#9e9e9e", "❓"))
    
    metrics_html = ""
    for k, v in metrics.items():
        if isinstance(v, float):
            metrics_html += f"<div style='margin: 5px 0;'><strong>{k}:</strong> {v:.4f}</div>"
        else:
            metrics_html += f"<div style='margin: 5px 0;'><strong>{k}:</strong> {v}</div>"
    
    return f'''
    <div style="border: 2px solid {color}; border-radius: 10px; padding: 15px; margin: 10px 0; background: white;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <h3 style="margin: 0; color: #333;">{title}</h3>
            <span style="font-size: 24px;">{icon}</span>
        </div>
        <div style="color: {color}; font-weight: bold; margin-bottom: 10px;">{status.value.upper()}</div>
        <div style="font-size: 14px; color: #666;">{metrics_html}</div>
    </div>
    '''


# =============================================================================
# STREAMLIT PAGE
# =============================================================================

def render_integration_import_page():
    """Render the enhanced Integration Import page."""
    
    st.title("📥 Integration Import Hub")
    st.markdown("""
    Import and analyze validation results from external tools. Parse results from 
    **ETAP**, **PSS/e**, and **Windchill RAM** to verify optimization configurations.
    """)
    
    # Initialize session state
    if 'validation_results' not in st.session_state:
        st.session_state.validation_results = []
    if 'constraint_updates' not in st.session_state:
        st.session_state.constraint_updates = []
    
    # Main tabs
    tab_dashboard, tab_etap, tab_psse, tab_ram, tab_demo = st.tabs([
        "📊 Validation Dashboard", "⚡ ETAP Import", "🔌 PSS/e Import",
        "📈 RAM Import", "🎯 Demo Mode"
    ])
    
    with tab_dashboard:
        render_validation_dashboard()
    
    with tab_etap:
        render_etap_import()
    
    with tab_psse:
        render_psse_import()
    
    with tab_ram:
        render_ram_import()
    
    with tab_demo:
        render_demo_mode()


def render_validation_dashboard():
    """Render the validation dashboard with status overview."""
    st.header("📊 Validation Dashboard")
    
    # Project status overview
    col1, col2, col3, col4 = st.columns(4)
    
    results = st.session_state.validation_results
    
    passed = sum(1 for r in results if r.status == ValidationStatus.PASSED)
    failed = sum(1 for r in results if r.status == ValidationStatus.FAILED)
    warnings = sum(1 for r in results if r.status == ValidationStatus.WARNING)
    pending = max(0, 4 - len(results))  # Assume 4 study types
    
    with col1:
        st.metric("✅ Passed", passed)
    with col2:
        st.metric("❌ Failed", failed)
    with col3:
        st.metric("⚠️ Warnings", warnings)
    with col4:
        st.metric("⏳ Pending", pending)
    
    st.divider()
    
    # Stage progress
    st.subheader("Validation Stages")
    
    stages = {
        'Stage 1: Screening': ValidationStatus.PASSED,  # Always assume optimization complete
        'Stage 2a: ETAP Load Flow': ValidationStatus.NOT_RUN,
        'Stage 2b: ETAP Short Circuit': ValidationStatus.NOT_RUN,
        'Stage 2c: PSS/e Power Flow': ValidationStatus.NOT_RUN,
        'Stage 3: RAM Analysis': ValidationStatus.NOT_RUN,
    }
    
    # Update from results
    for r in results:
        if r.tool == "ETAP" and "Load Flow" in r.study_type:
            stages['Stage 2a: ETAP Load Flow'] = r.status
        elif r.tool == "ETAP" and "Short Circuit" in r.study_type:
            stages['Stage 2b: ETAP Short Circuit'] = r.status
        elif r.tool == "PSS/e":
            stages['Stage 2c: PSS/e Power Flow'] = r.status
        elif r.tool == "Windchill RAM":
            stages['Stage 3: RAM Analysis'] = r.status
    
    for stage, status in stages.items():
        icon = {
            ValidationStatus.PASSED: "✅",
            ValidationStatus.FAILED: "❌",
            ValidationStatus.WARNING: "⚠️",
            ValidationStatus.PENDING: "⏳",
            ValidationStatus.NOT_RUN: "⬜",
        }.get(status, "❓")
        
        st.markdown(f"{icon} **{stage}**: {status.value}")
    
    st.divider()
    
    # Detailed results
    if results:
        st.subheader("Detailed Results")
        
        for result in results:
            with st.expander(f"{result.tool} - {result.study_type} ({result.status.value.upper()})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Metrics:**")
                    for k, v in result.metrics.items():
                        st.write(f"- {k}: {v:.4f}" if isinstance(v, float) else f"- {k}: {v}")
                
                with col2:
                    if result.violations:
                        st.markdown("**❌ Violations:**")
                        for v in result.violations:
                            st.error(v)
                    
                    if result.warnings:
                        st.markdown("**⚠️ Warnings:**")
                        for w in result.warnings:
                            st.warning(w)
                    
                    if result.recommendations:
                        st.markdown("**💡 Recommendations:**")
                        for r in result.recommendations:
                            st.info(r)
    
    # Constraint updates
    if st.session_state.constraint_updates:
        st.divider()
        st.subheader("🔧 Suggested Constraint Updates")
        
        for i, update in enumerate(st.session_state.constraint_updates):
            with st.expander(f"**{update.constraint_name}** - {update.priority}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Current", f"{update.current_value}")
                with col2:
                    st.metric("Suggested", f"{update.suggested_value}")
                
                st.markdown(f"**Reason:** {update.reason}")
                st.markdown(f"**Impact:** {update.impact}")
                
                if st.button("Apply Update", key=f"apply_{i}"):
                    st.success(f"Applied constraint update: {update.constraint_name}")


def render_etap_import():
    """Render ETAP import interface."""
    st.header("⚡ ETAP Results Import")
    
    study_type = st.selectbox(
        "Study Type",
        ["Load Flow", "Short Circuit", "Arc Flash"],
        key="etap_study"
    )
    
    st.markdown(f"### Expected {study_type} Results Format")
    
    if study_type == "Load Flow":
        sample_df = generate_sample_etap_lf_results("pass")
        st.dataframe(sample_df, use_container_width=True, hide_index=True)
        
        st.markdown("""
        **Required columns:**
        - `Bus_ID` or `Bus`: Bus identifier
        - `Voltage_pu` or `V_pu`: Per-unit voltage
        - `Loading_pct` or `Load%`: Equipment loading percentage
        """)
    else:
        sample_df = generate_sample_etap_sc_results("pass")
        st.dataframe(sample_df, use_container_width=True, hide_index=True)
        
        st.markdown("""
        **Required columns:**
        - `Bus_ID` or `Bus`: Bus identifier
        - `Isc_kA` or `Fault_kA`: Fault current in kA
        - `Duty_pct` or `Breaker_Duty`: Breaker duty percentage
        """)
    
    st.divider()
    
    uploaded = st.file_uploader("Upload ETAP Results", type=['csv', 'xlsx'], key="etap_upload")
    
    if uploaded:
        try:
            if uploaded.name.endswith('.csv'):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)
            
            st.success(f"Loaded {len(df)} rows")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            if st.button("Analyze Results", key="analyze_etap"):
                if study_type == "Load Flow":
                    result = parse_etap_loadflow(df)
                else:
                    result = parse_etap_shortcircuit(df)
                
                result.source_file = uploaded.name
                st.session_state.validation_results.append(result)
                
                updates = generate_constraint_updates(result)
                st.session_state.constraint_updates.extend(updates)
                
                if result.status == ValidationStatus.PASSED:
                    st.success("✅ Validation PASSED")
                elif result.status == ValidationStatus.WARNING:
                    st.warning("⚠️ Validation passed with WARNINGS")
                else:
                    st.error("❌ Validation FAILED")
                
                st.rerun()
                
        except Exception as e:
            st.error(f"Error: {e}")


def render_psse_import():
    """Render PSS/e import interface."""
    st.header("🔌 PSS/e Results Import")
    
    st.markdown("### Expected Power Flow Results Format")
    sample_df = generate_sample_psse_results("pass")
    st.dataframe(sample_df, use_container_width=True, hide_index=True)
    
    st.markdown("""
    **Required columns:**
    - `BUS`: Bus number
    - `VM_PU` or `Voltage_pu`: Per-unit voltage magnitude
    - `VA_DEG` or `Angle_deg`: Voltage angle in degrees
    """)
    
    st.divider()
    
    uploaded = st.file_uploader("Upload PSS/e Results", type=['csv', 'xlsx', 'txt'], key="psse_upload")
    
    if uploaded:
        try:
            if uploaded.name.endswith('.csv'):
                df = pd.read_csv(uploaded)
            elif uploaded.name.endswith('.xlsx'):
                df = pd.read_excel(uploaded)
            else:
                content = uploaded.read().decode('utf-8')
                df = pd.read_csv(io.StringIO(content), sep=r'\s+')
            
            st.success(f"Loaded {len(df)} rows")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            if st.button("Analyze Results", key="analyze_psse"):
                result = parse_psse_results(df)
                result.source_file = uploaded.name
                st.session_state.validation_results.append(result)
                
                updates = generate_constraint_updates(result)
                st.session_state.constraint_updates.extend(updates)
                
                if result.status == ValidationStatus.PASSED:
                    st.success("✅ Validation PASSED")
                else:
                    st.error("❌ Validation FAILED")
                
                st.rerun()
                
        except Exception as e:
            st.error(f"Error: {e}")


def render_ram_import():
    """Render Windchill RAM import interface."""
    st.header("📈 Windchill RAM Results Import")
    
    st.markdown("### Expected RAM Analysis Results Format")
    sample_df = generate_sample_ram_results("pass")
    st.dataframe(sample_df, use_container_width=True, hide_index=True)
    
    st.markdown("""
    **Required columns:**
    - `Block_ID`: Block/subsystem identifier
    - `Availability`: System availability (0-1 or percentage)
    - `Annual_Downtime_Hours` or `Downtime`: Hours per year
    """)
    
    st.divider()
    
    uploaded = st.file_uploader("Upload RAM Results", type=['csv', 'xlsx'], key="ram_upload")
    
    if uploaded:
        try:
            if uploaded.name.endswith('.csv'):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)
            
            st.success(f"Loaded {len(df)} rows")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            if st.button("Analyze Results", key="analyze_ram"):
                result = parse_ram_results(df)
                result.source_file = uploaded.name
                st.session_state.validation_results.append(result)
                
                updates = generate_constraint_updates(result)
                st.session_state.constraint_updates.extend(updates)
                
                if result.status == ValidationStatus.PASSED:
                    st.success("✅ Validation PASSED")
                else:
                    st.error("❌ Validation FAILED")
                
                st.rerun()
                
        except Exception as e:
            st.error(f"Error: {e}")


def render_demo_mode():
    """Render demo mode with sample results."""
    st.header("🎯 Demo Mode")
    st.markdown("""
    Load sample results to see how the validation workflow works.
    Choose scenarios that pass or fail validation to see constraint feedback.
    """)
    
    scenario = st.radio(
        "Select Demo Scenario",
        ["All Pass", "RAM Fail (Availability)", "ETAP Fail (Voltage)", "ETAP Fail (Short Circuit)"],
    )
    
    if st.button("Load Demo Results"):
        # Clear existing
        st.session_state.validation_results = []
        st.session_state.constraint_updates = []
        
        if scenario == "All Pass":
            # Load all passing results
            r1 = parse_etap_loadflow(generate_sample_etap_lf_results("pass"))
            r2 = parse_etap_shortcircuit(generate_sample_etap_sc_results("pass"))
            r3 = parse_psse_results(generate_sample_psse_results("pass"))
            r4 = parse_ram_results(generate_sample_ram_results("pass"))
            st.session_state.validation_results = [r1, r2, r3, r4]
            st.success("✅ All validations passed!")
            
        elif scenario == "RAM Fail (Availability)":
            r1 = parse_etap_loadflow(generate_sample_etap_lf_results("pass"))
            r2 = parse_etap_shortcircuit(generate_sample_etap_sc_results("pass"))
            r3 = parse_psse_results(generate_sample_psse_results("pass"))
            r4 = parse_ram_results(generate_sample_ram_results("fail"))
            st.session_state.validation_results = [r1, r2, r3, r4]
            st.session_state.constraint_updates = generate_constraint_updates(r4)
            st.error("❌ RAM analysis failed - see constraint updates")
            
        elif scenario == "ETAP Fail (Voltage)":
            r1 = parse_etap_loadflow(generate_sample_etap_lf_results("fail"))
            r2 = parse_etap_shortcircuit(generate_sample_etap_sc_results("pass"))
            r3 = parse_psse_results(generate_sample_psse_results("pass"))
            r4 = parse_ram_results(generate_sample_ram_results("pass"))
            st.session_state.validation_results = [r1, r2, r3, r4]
            st.session_state.constraint_updates = generate_constraint_updates(r1)
            st.error("❌ ETAP load flow failed - voltage violations")
            
        else:  # Short Circuit Fail
            r1 = parse_etap_loadflow(generate_sample_etap_lf_results("pass"))
            r2 = parse_etap_shortcircuit(generate_sample_etap_sc_results("fail"))
            r3 = parse_psse_results(generate_sample_psse_results("pass"))
            r4 = parse_ram_results(generate_sample_ram_results("pass"))
            st.session_state.validation_results = [r1, r2, r3, r4]
            st.session_state.constraint_updates = generate_constraint_updates(r2)
            st.error("❌ ETAP short circuit failed - breaker duty exceeded")
        
        st.rerun()
    
    if st.button("Clear All Results"):
        st.session_state.validation_results = []
        st.session_state.constraint_updates = []
        st.success("Cleared all results")
        st.rerun()


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    st.set_page_config(
        page_title="bvNexus - Integration Import",
        page_icon="📥",
        layout="wide"
    )
    render_integration_import_page()
