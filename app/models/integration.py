"""
Integration Data Models for External Tool Validation
=====================================================

Data models for integrating with external power systems analysis tools:
- ETAP (Electrical Transient Analysis Program)
- PSS/e (Power System Simulator for Engineering)
- Windchill RAM (Reliability, Availability, Maintainability)

These models support exporting optimization results to external tools
and importing validation results back into the optimizer for refinement.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class ValidationStatus(Enum):
    """Status of a validation result from external tool."""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    NOT_RUN = "not_run"


@dataclass
class ValidationResult:
    """
    Result from external validation tool analysis.
    
    Contains metrics, violations, warnings, and recommendations
    from running ETAP, PSS/e, or Windchill RAM studies.
    """
    result_id: str
    tool: str                           # "ETAP", "PSS/e", "Windchill RAM"
    study_type: str                     # "Load Flow", "Short Circuit", "Power Flow", "Availability Analysis"
    timestamp: datetime
    status: ValidationStatus
    metrics: Dict[str, float] = field(default_factory=dict)
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    source_file: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'result_id': self.result_id,
            'tool': self.tool,
            'study_type': self.study_type,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp),
            'status': self.status.value,
            'metrics': self.metrics,
            'violations': self.violations,
            'warnings': self.warnings,
            'recommendations': self.recommendations,
            'source_file': self.source_file,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ValidationResult':
        """Create from dictionary."""
        # Convert timestamp string back to datetime
        timestamp = data.get('timestamp', datetime.now())
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        # Convert status string back to enum
        status = data.get('status', 'pending')
        if isinstance(status, str):
            status = ValidationStatus(status)
        
        return cls(
            result_id=data['result_id'],
            tool=data['tool'],
            study_type=data['study_type'],
            timestamp=timestamp,
            status=status,
            metrics=data.get('metrics', {}),
            violations=data.get('violations', []),
            warnings=data.get('warnings', []),
            recommendations=data.get('recommendations', []),
            source_file=data.get('source_file', ''),
        )


@dataclass
class ConstraintUpdate:
    """
    Suggested constraint update based on validation results.
    
    When external tool analysis identifies a violation, this suggests
    how to update the optimization constraints to address the issue.
    """
    constraint_name: str
    current_value: float
    suggested_value: float
    reason: str
    source_study: str
    priority: str                       # "Critical", "High", "Medium", "Low"
    impact: str = ""
    applied:bool = False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'constraint_name': self.constraint_name,
            'current_value': self.current_value,
            'suggested_value': self.suggested_value,
            'reason': self.reason,
            'source_study': self.source_study,
            'priority': self.priority,
            'impact': self.impact,
            'applied': self.applied,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ConstraintUpdate':
        """Create from dictionary."""
        return cls(
            constraint_name=data['constraint_name'],
            current_value=data['current_value'],
            suggested_value=data['suggested_value'],
            reason=data['reason'],
            source_study=data['source_study'],
            priority=data['priority'],
            impact=data.get('impact', ''),
            applied=data.get('applied', False),
        )


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
# EQUIPMENT EXPORT FORMATS
# =============================================================================

@dataclass
class ETAPEquipmentExport:
    """
    Equipment data formatted for ETAP import.
    """
    equipment_id: str
    name: str
    equipment_type: str                 # "Synchronous Generator", "Battery", "Transformer"
    bus_id: str
    rated_kv: float
    rated_mw: float
    rated_mva: float
    rated_pf: float = 0.85
    xd_pu: float = 1.8
    xd_prime_pu: float = 0.25
    xd_double_prime_pu: float = 0.18
    h_inertia_sec: float = 1.5
    status: str = "Online"


@dataclass
class PSSeBusData:
    """
    Bus data for PSS/e RAW format export.
    """
    bus_number: int
    bus_name: str
    base_kv: float
    bus_type: int = 1                   # 1=load, 2=gen, 3=swing
    area: int = 1
    zone: int = 1
    owner: int = 1
    vm_pu: float = 1.0
    va_deg: float = 0.0


@dataclass
class PSSeGeneratorData:
    """
    Generator data for PSS/e RAW format export.
    """
    bus_number: int
    gen_id: str
    pg_mw: float
    qg_mvar: float
    qt_mvar: float                      # Max reactive
    qb_mvar: float                      # Min reactive
    vs_pu: float = 1.0
    ireg: int = 0                       # Regulated bus
    mbase_mva: float = 100.0


@dataclass
class WindchillComponentData:
    """
    Component data for Windchill RAM import.
    """
    component_id: str
    component_name: str
    component_type: str                 # "RECIPROCATING_ENGINE", "GAS_TURBINE", "BATTERY", etc.
    mtbf_hours: float
    mttr_hours: float
    failure_rate_per_hour: float
    availability: float
    distribution: str = "Exponential"
    weibull_beta: float = 1.0
    
    @staticmethod
    def calculate_availability(mtbf: float, mttr: float) -> float:
        """Calculate availability from MTBF and MTTR."""
        return mtbf / (mtbf + mttr)
    
    @staticmethod
    def calculate_failure_rate(mtbf: float) -> float:
        """Calculate failure rate from MTBF."""
        return 1.0 / mtbf if mtbf > 0 else 0.0


@dataclass
class WindchillRBDBlock:
    """
    Reliability Block Diagram structure for Windchill RAM.
    """
    block_id: str
    block_name: str
    block_type: str                     # "SERIES", "PARALLEL", "PARALLEL_K_OF_N"
    components: List[str]               # Component IDs
    k_required: int                     # For K-of-N redundancy
    n_total: int                        # Total count
    description: str = ""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_validation_color(status: ValidationStatus) -> str:
    """Get color code for validation status."""
    return {
        ValidationStatus.PASSED: "#4CAF50",
        ValidationStatus.FAILED: "#f44336",
        ValidationStatus.WARNING: "#FFC107",
        ValidationStatus.PENDING: "#9e9e9e",
        ValidationStatus.NOT_RUN: "#9e9e9e",
    }.get(status, "#9e9e9e")


def get_validation_icon(status: ValidationStatus) -> str:
    """Get icon for validation status."""
    return {
        ValidationStatus.PASSED: "✅",
        ValidationStatus.FAILED: "❌",
        ValidationStatus.WARNING: "⚠️",
        ValidationStatus.PENDING: "⏳",
        ValidationStatus.NOT_RUN: "⬜",
    }.get(status, "❓")
