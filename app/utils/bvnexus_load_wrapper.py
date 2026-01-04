"""
bvNexus Load Integration Wrapper
================================

Integration layer connecting bvnexus_load_module.py to:
- Streamlit UI pages (Load Composer, Engineering Drawings)
- Pyomo optimizer (design.py, dispatch.py)
- Export generators (PSS/e, ETAP, RAM)
- Google Sheets data layer

This wrapper follows the Two-Stage Decomposition architecture:
- Stage 1: MILP Design Phase (capacity expansion with representative periods)
- Stage 2: LP Validation Phase (full 8760 dispatch with fixed capacities)

Author: bvNexus Engineering Integration
Version: 1.0.0
Date: 2026-01-03

Usage in Antigravity:
    from bvnexus_load_wrapper import LoadManager, StreamlitLoadPage
    
    # For Streamlit pages
    load_page = StreamlitLoadPage()
    load_page.render()
    
    # For optimizer integration
    manager = LoadManager()
    params = manager.get_optimizer_parameters(site_id="SITE_001")
"""

from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import json
import math
import logging

# Import the core load module
try:
    from bvnexus_load_module import (
        LoadPageConfig,
        WorkloadMix,
        LoadComposition,
        calculate_load_composition,
        calculate_load_breakdown,
        get_pyomo_load_parameters,
        get_load_profile_multipliers,
        generate_psse_dyr_parameters,
        generate_etap_data,
        generate_ram_data,
        COOLING_SPECS,
        WORKLOAD_SPECS,
        ISO_PROFILES,
        IEEE_493_RELIABILITY,
        HARMONIC_SOURCES,
    )
except ImportError:
    # Fallback for development - assume module is in same directory
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from bvnexus_load_module import (
        LoadPageConfig,
        WorkloadMix,
        LoadComposition,
        calculate_load_composition,
        calculate_load_breakdown,
        get_pyomo_load_parameters,
        get_load_profile_multipliers,
        generate_psse_dyr_parameters,
        generate_etap_data,
        generate_ram_data,
        COOLING_SPECS,
        WORKLOAD_SPECS,
        ISO_PROFILES,
        IEEE_493_RELIABILITY,
        HARMONIC_SOURCES,
    )


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bvnexus.load_wrapper")


# =============================================================================
# SECTION 1: DATA TRANSFER OBJECTS (DTOs)
# =============================================================================

@dataclass
class SiteLoadConfig:
    """
    Site-level load configuration from Google Sheets or Streamlit.
    
    This is the canonical transfer object between the UI and optimizer.
    """
    site_id: str
    site_name: str
    peak_load_mw: float
    pue: float
    cooling_type: str
    iso_region: str
    
    # Workload mix (percentages 0-100)
    pre_training_pct: float = 30.0
    fine_tuning_pct: float = 20.0
    batch_inference_pct: float = 30.0
    realtime_inference_pct: float = 20.0
    
    # Optional overrides
    custom_flexibility_pct: Optional[float] = None
    custom_power_factor: Optional[float] = None
    
    def to_load_page_config(self) -> LoadPageConfig:
        """Convert to core module config format."""
        return LoadPageConfig(
            peak_load_mw=self.peak_load_mw,
            pue=self.pue,
            cooling_type=self.cooling_type,
            workload_mix=WorkloadMix(
                pre_training=self.pre_training_pct / 100.0,
                fine_tuning=self.fine_tuning_pct / 100.0,
                batch_inference=self.batch_inference_pct / 100.0,
                realtime_inference=self.realtime_inference_pct / 100.0,
            ),
            iso_region=self.iso_region,
        )
    
    @classmethod
    def from_sheets_row(cls, row: Dict[str, Any]) -> "SiteLoadConfig":
        """
        Create from Google Sheets row format.
        
        Expected columns:
        - site_id, site_name, peak_load_mw, pue, cooling_type, iso_region
        - pre_training_pct, fine_tuning_pct, batch_inference_pct, realtime_inference_pct
        """
        return cls(
            site_id=str(row.get("site_id", "UNKNOWN")),
            site_name=str(row.get("site_name", "Unnamed Site")),
            peak_load_mw=float(row.get("peak_load_mw", 100)),
            pue=float(row.get("pue", 1.3)),
            cooling_type=str(row.get("cooling_type", "rear_door_heat_exchanger")),
            iso_region=str(row.get("iso_region", "generic")),
            pre_training_pct=float(row.get("pre_training_pct", 30)),
            fine_tuning_pct=float(row.get("fine_tuning_pct", 20)),
            batch_inference_pct=float(row.get("batch_inference_pct", 30)),
            realtime_inference_pct=float(row.get("realtime_inference_pct", 20)),
            custom_flexibility_pct=row.get("custom_flexibility_pct"),
            custom_power_factor=row.get("custom_power_factor"),
        )
    
    def to_sheets_row(self) -> Dict[str, Any]:
        """Convert to Google Sheets row format."""
        return asdict(self)


@dataclass
class OptimizerLoadInput:
    """
    Load parameters formatted for Pyomo optimizer.
    
    Used by design.py (Stage 1) and dispatch.py (Stage 2).
    """
    # Identification
    site_id: str
    
    # Load Parameters
    peak_load_mw: float
    it_load_mw: float
    cooling_load_mw: float
    pue: float
    power_factor: float
    
    # Demand Response Parameters
    flexibility_pct: float
    dr_capacity_mw: float
    economic_dr_mw: float
    ers_30_mw: float
    ers_10_mw: float
    min_curtailment_hr: float
    
    # Equipment Counts (for reliability)
    ups_count: int
    chiller_count: int
    
    # ISO Compliance
    requires_llis: bool
    iso_region: str
    
    # Time Series (optional, for dispatch phase)
    load_profile_multipliers: Optional[List[float]] = None
    
    def to_pyomo_params(self) -> Dict[str, Any]:
        """Get as dictionary for Pyomo model.parameters()."""
        params = {
            "peak_load_mw": self.peak_load_mw,
            "it_load_mw": self.it_load_mw,
            "cooling_load_mw": self.cooling_load_mw,
            "pue": self.pue,
            "power_factor": self.power_factor,
            "flexibility_pct": self.flexibility_pct,
            "dr_capacity_mw": self.dr_capacity_mw,
            "economic_dr_mw": self.economic_dr_mw,
            "ers_30_mw": self.ers_30_mw,
            "ers_10_mw": self.ers_10_mw,
            "min_curtailment_hr": self.min_curtailment_hr,
            "ups_count": self.ups_count,
            "chiller_count": self.chiller_count,
            "requires_llis": 1 if self.requires_llis else 0,
        }
        return params


@dataclass
class ExportPackage:
    """
    Complete export package for engineering tools.
    
    Contains all data needed for PSS/e, ETAP, and RAM studies.
    """
    site_id: str
    site_name: str
    timestamp: str
    
    # PSS/e Dynamic Model
    psse_dyr_content: str
    psse_bus_number: int
    
    # ETAP Data
    etap_json: Dict[str, Any]
    
    # RAM Data
    ram_json: Dict[str, Any]
    
    # Summary
    summary: Dict[str, Any]
    
    def save_to_directory(self, output_dir: Path) -> Dict[str, Path]:
        """
        Save all export files to directory.
        
        Returns:
            Dictionary of file types to paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        files = {}
        
        # PSS/e DYR file
        dyr_path = output_dir / f"{self.site_id}_load_model.dyr"
        dyr_path.write_text(self.psse_dyr_content)
        files["psse_dyr"] = dyr_path
        
        # ETAP JSON
        etap_path = output_dir / f"{self.site_id}_etap_data.json"
        etap_path.write_text(json.dumps(self.etap_json, indent=2))
        files["etap_json"] = etap_path
        
        # RAM JSON
        ram_path = output_dir / f"{self.site_id}_ram_data.json"
        ram_path.write_text(json.dumps(self.ram_json, indent=2))
        files["ram_json"] = ram_path
        
        # Summary JSON
        summary_path = output_dir / f"{self.site_id}_summary.json"
        summary_path.write_text(json.dumps(self.summary, indent=2))
        files["summary"] = summary_path
        
        logger.info(f"Saved export package to {output_dir}")
        return files


# =============================================================================
# SECTION 2: LOAD MANAGER (Core Integration Class)
# =============================================================================

class LoadManager:
    """
    Central manager for load calculations and integrations.
    
    This is the primary interface for the optimizer and UI components.
    
    Example:
        manager = LoadManager()
        
        # Add site configuration
        manager.add_site(SiteLoadConfig(
            site_id="SITE_001",
            site_name="Texas DC",
            peak_load_mw=200,
            pue=1.3,
            cooling_type="rear_door_heat_exchanger",
            iso_region="ercot",
        ))
        
        # Get optimizer parameters
        params = manager.get_optimizer_parameters("SITE_001")
        
        # Generate export package
        export = manager.generate_export_package("SITE_001")
    """
    
    def __init__(self):
        self._sites: Dict[str, SiteLoadConfig] = {}
        self._compositions: Dict[str, LoadComposition] = {}
        self._load_profiles: Dict[str, List[float]] = {}
        
    def add_site(self, config: SiteLoadConfig) -> LoadComposition:
        """
        Add or update a site configuration.
        
        Args:
            config: Site load configuration
            
        Returns:
            Calculated load composition
        """
        self._sites[config.site_id] = config
        
        # Calculate composition
        load_config = config.to_load_page_config()
        composition = calculate_load_composition(load_config)
        self._compositions[config.site_id] = composition
        
        # Generate load profile
        profile = get_load_profile_multipliers(load_config.workload_mix)
        self._load_profiles[config.site_id] = profile
        
        logger.info(f"Added site {config.site_id}: {config.peak_load_mw} MW, PUE={config.pue}")
        return composition
    
    def get_site_config(self, site_id: str) -> Optional[SiteLoadConfig]:
        """Get site configuration by ID."""
        return self._sites.get(site_id)
    
    def get_composition(self, site_id: str) -> Optional[LoadComposition]:
        """Get calculated load composition by site ID."""
        return self._compositions.get(site_id)
    
    def get_load_profile(self, site_id: str) -> Optional[List[float]]:
        """Get 8760 hourly load profile multipliers."""
        return self._load_profiles.get(site_id)
    
    def get_optimizer_parameters(self, site_id: str) -> Optional[OptimizerLoadInput]:
        """
        Get load parameters formatted for Pyomo optimizer.
        
        Args:
            site_id: Site identifier
            
        Returns:
            OptimizerLoadInput ready for Pyomo, or None if site not found
        """
        composition = self._compositions.get(site_id)
        if composition is None:
            logger.warning(f"Site {site_id} not found")
            return None
        
        params = get_pyomo_load_parameters(composition)
        profile = self._load_profiles.get(site_id)
        
        return OptimizerLoadInput(
            site_id=site_id,
            peak_load_mw=params["peak_load_mw"],
            it_load_mw=params["it_load_mw"],
            cooling_load_mw=params["cooling_load_mw"],
            pue=params["pue"],
            power_factor=params["power_factor"],
            flexibility_pct=params["flexibility_pct"],
            dr_capacity_mw=params["dr_capacity_mw"],
            economic_dr_mw=params["economic_dr_mw"],
            ers_30_mw=params["ers_30_mw"],
            ers_10_mw=params["ers_10_mw"],
            min_curtailment_hr=params["min_curtailment_hr"],
            ups_count=params["ups_count"],
            chiller_count=params["chiller_count"],
            requires_llis=params["requires_llis"],
            iso_region=params["iso_region"],
            load_profile_multipliers=profile,
        )
    
    def generate_export_package(
        self,
        site_id: str,
        bus_number: int = 401001
    ) -> Optional[ExportPackage]:
        """
        Generate complete export package for engineering tools.
        
        Args:
            site_id: Site identifier
            bus_number: PSS/e bus number for load model
            
        Returns:
            ExportPackage with all engineering data
        """
        from datetime import datetime
        
        config = self._sites.get(site_id)
        composition = self._compositions.get(site_id)
        
        if config is None or composition is None:
            logger.warning(f"Site {site_id} not found")
            return None
        
        # Generate PSS/e DYR content
        dyr_content = generate_psse_dyr_parameters(
            composition,
            bus_number=bus_number,
            load_id="1"
        )
        
        # Generate ETAP data
        etap_data = generate_etap_data(composition, site_id=site_id)
        
        # Generate RAM data
        ram_data = generate_ram_data(composition, site_id=site_id)
        
        # Build summary
        f = composition.psse_fractions
        summary = {
            "site_id": site_id,
            "site_name": config.site_name,
            "generated_at": datetime.now().isoformat(),
            "load_summary": {
                "total_mw": composition.total_mw,
                "it_load_mw": composition.it_load_mw,
                "cooling_load_mw": composition.cooling_load_mw,
                "pue": composition.pue_actual,
                "power_factor": composition.power_factor,
            },
            "psse_fractions": f.to_dict(),
            "electronic_load_pct": f.fel * 100,
            "motor_load_pct": (f.fma + f.fmb + f.fmc + f.fmd) * 100,
            "flexibility": {
                "weighted_pct": composition.flexibility.weighted_flexibility_pct,
                "dr_capacity_mw": composition.flexibility.dr_capacity_mw,
            },
            "iso_compliance": {
                "region": composition.iso_region,
                "requires_llis": composition.requires_llis,
                "vrt_profile": composition.voltage_ride_through.get("profile", "N/A"),
            },
            "harmonics": {
                "thd_v_pct": composition.harmonics.thd_v,
                "thd_i_pct": composition.harmonics.thd_i,
                "ieee_519_compliant": composition.harmonics.ieee_519_compliant,
            },
            "availability": ram_data["availability"],
        }
        
        return ExportPackage(
            site_id=site_id,
            site_name=config.site_name,
            timestamp=datetime.now().isoformat(),
            psse_dyr_content=dyr_content,
            psse_bus_number=bus_number,
            etap_json=etap_data,
            ram_json=ram_data,
            summary=summary,
        )
    
    def bulk_load_from_sheets(self, rows: List[Dict[str, Any]]) -> int:
        """
        Bulk load site configurations from Google Sheets data.
        
        Args:
            rows: List of row dictionaries from Google Sheets
            
        Returns:
            Number of sites loaded successfully
        """
        count = 0
        for row in rows:
            try:
                config = SiteLoadConfig.from_sheets_row(row)
                self.add_site(config)
                count += 1
            except Exception as e:
                logger.error(f"Failed to load row: {e}")
        
        logger.info(f"Loaded {count} of {len(rows)} sites from sheets data")
        return count
    
    def list_sites(self) -> List[str]:
        """List all configured site IDs."""
        return list(self._sites.keys())


# =============================================================================
# SECTION 3: STREAMLIT PAGE COMPONENTS
# =============================================================================

class StreamlitLoadPage:
    """
    Streamlit page component for Load Composer.
    
    Provides UI widgets for configuring datacenter loads and
    previewing calculations before optimization.
    
    Usage:
        import streamlit as st
        from bvnexus_load_wrapper import StreamlitLoadPage
        
        page = StreamlitLoadPage()
        page.render()
    """
    
    def __init__(self, manager: Optional[LoadManager] = None):
        self.manager = manager or LoadManager()
        self._current_config: Optional[SiteLoadConfig] = None
        self._current_composition: Optional[LoadComposition] = None
    
    def render(self):
        """Render the complete Load Composer page."""
        try:
            import streamlit as st
        except ImportError:
            raise ImportError("Streamlit required for UI components. Install with: pip install streamlit")
        
        st.header("🔌 Load Composer")
        st.markdown("*Configure AI datacenter load characteristics for optimization*")
        
        # Create tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Basic Configuration",
            "⚙️ Workload Mix", 
            "📈 Calculated Results",
            "📤 Export"
        ])
        
        with tab1:
            self._render_basic_config(st)
        
        with tab2:
            self._render_workload_config(st)
        
        with tab3:
            self._render_results(st)
        
        with tab4:
            self._render_export(st)
    
    def _render_basic_config(self, st):
        """Render basic configuration inputs."""
        col1, col2 = st.columns(2)
        
        with col1:
            site_id = st.text_input("Site ID", value="SITE_001")
            site_name = st.text_input("Site Name", value="New Datacenter")
            peak_load = st.number_input(
                "Peak Load (MW)", 
                min_value=1.0, 
                max_value=5000.0, 
                value=200.0,
                step=10.0
            )
        
        with col2:
            cooling_options = list(COOLING_SPECS.keys())
            cooling_names = [COOLING_SPECS[c]["name"] for c in cooling_options]
            cooling_idx = st.selectbox(
                "Cooling Type",
                range(len(cooling_options)),
                format_func=lambda i: cooling_names[i],
                index=1  # Default to rear-door heat exchanger
            )
            cooling_type = cooling_options[cooling_idx]
            
            # Get PUE range for selected cooling type
            pue_range = COOLING_SPECS[cooling_type]["pue_range"]
            pue_typical = COOLING_SPECS[cooling_type]["pue_typical"]
            
            pue = st.slider(
                "PUE",
                min_value=float(pue_range[0]),
                max_value=float(pue_range[1]),
                value=float(pue_typical),
                step=0.01,
                help=f"Typical for {COOLING_SPECS[cooling_type]['name']}: {pue_typical}"
            )
            
            iso_options = list(ISO_PROFILES.keys())
            iso_names = [ISO_PROFILES[i]["name"] for i in iso_options]
            iso_idx = st.selectbox(
                "ISO/RTO Region",
                range(len(iso_options)),
                format_func=lambda i: iso_names[i],
                index=0  # Default to ERCOT
            )
            iso_region = iso_options[iso_idx]
        
        # Store in session state
        if "load_config" not in st.session_state:
            st.session_state.load_config = {}
        
        st.session_state.load_config.update({
            "site_id": site_id,
            "site_name": site_name,
            "peak_load_mw": peak_load,
            "pue": pue,
            "cooling_type": cooling_type,
            "iso_region": iso_region,
        })
    
    def _render_workload_config(self, st):
        """Render workload mix configuration."""
        st.subheader("AI Workload Mix")
        st.markdown("*Adjust sliders to match your expected workload distribution*")
        
        # Get workload specs for display
        workload_help = {
            "Pre-Training": f"Flexibility: {WORKLOAD_SPECS['pre_training']['flexibility_pct']}% | Checkpoint overhead: {WORKLOAD_SPECS['pre_training']['checkpoint_overhead_pct']}%",
            "Fine-Tuning": f"Flexibility: {WORKLOAD_SPECS['fine_tuning']['flexibility_pct']}% | Checkpoint overhead: {WORKLOAD_SPECS['fine_tuning']['checkpoint_overhead_pct']}%",
            "Batch Inference": f"Flexibility: {WORKLOAD_SPECS['batch_inference']['flexibility_pct']}% | Checkpoint overhead: {WORKLOAD_SPECS['batch_inference']['checkpoint_overhead_pct']}%",
            "Real-Time Inference": f"Flexibility: {WORKLOAD_SPECS['realtime_inference']['flexibility_pct']}% | Not curtailable",
        }
        
        col1, col2 = st.columns(2)
        
        with col1:
            pre_training = st.slider(
                "Pre-Training (%)",
                min_value=0,
                max_value=100,
                value=30,
                help=workload_help["Pre-Training"]
            )
            
            fine_tuning = st.slider(
                "Fine-Tuning (%)",
                min_value=0,
                max_value=100,
                value=20,
                help=workload_help["Fine-Tuning"]
            )
        
        with col2:
            batch_inference = st.slider(
                "Batch Inference (%)",
                min_value=0,
                max_value=100,
                value=30,
                help=workload_help["Batch Inference"]
            )
            
            realtime_inference = st.slider(
                "Real-Time Inference (%)",
                min_value=0,
                max_value=100,
                value=20,
                help=workload_help["Real-Time Inference"]
            )
        
        total = pre_training + fine_tuning + batch_inference + realtime_inference
        
        if total != 100:
            st.warning(f"⚠️ Total workload mix is {total}% (should be 100%)")
        else:
            st.success("✅ Workload mix sums to 100%")
        
        # Update session state
        st.session_state.load_config.update({
            "pre_training_pct": pre_training,
            "fine_tuning_pct": fine_tuning,
            "batch_inference_pct": batch_inference,
            "realtime_inference_pct": realtime_inference,
        })
    
    def _render_results(self, st):
        """Render calculated results preview."""
        config_dict = st.session_state.get("load_config", {})
        
        if not config_dict:
            st.info("Configure load parameters in previous tabs")
            return
        
        # Validate workload sum
        total_workload = sum([
            config_dict.get("pre_training_pct", 30),
            config_dict.get("fine_tuning_pct", 20),
            config_dict.get("batch_inference_pct", 30),
            config_dict.get("realtime_inference_pct", 20),
        ])
        
        if total_workload != 100:
            st.error("Fix workload mix before calculating")
            return
        
        # Calculate button
        if st.button("🔄 Calculate Load Composition", type="primary"):
            try:
                config = SiteLoadConfig(**config_dict)
                composition = self.manager.add_site(config)
                self._current_config = config
                self._current_composition = composition
                st.session_state["composition_calculated"] = True
            except Exception as e:
                st.error(f"Calculation error: {e}")
                return
        
        # Show results if calculated
        if st.session_state.get("composition_calculated") and self._current_composition:
            self._display_composition_results(st, self._current_composition)
    
    def _display_composition_results(self, st, comp: LoadComposition):
        """Display calculated composition results."""
        st.subheader("📊 Load Breakdown")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Load", f"{comp.total_mw:.1f} MW")
            st.metric("IT Load", f"{comp.it_load_mw:.1f} MW")
        
        with col2:
            st.metric("Cooling Load", f"{comp.cooling_load_mw:.1f} MW")
            st.metric("PUE", f"{comp.pue_actual:.2f}")
        
        with col3:
            st.metric("Power Factor", f"{comp.power_factor:.2f}")
            st.metric("DR Capacity", f"{comp.flexibility.dr_capacity_mw:.1f} MW")
        
        # PSS/e Fractions
        st.subheader("⚡ PSS/e CMPLDW Load Fractions")
        
        f = comp.psse_fractions
        fractions_data = {
            "Component": ["Electronic (GPU/TPU)", "Motor A (Fans)", "Motor B (Chillers)", 
                         "Motor C (Compressors)", "Motor D (VFD)", "Static"],
            "Fraction (%)": [f.fel*100, f.fma*100, f.fmb*100, f.fmc*100, f.fmd*100, f.pfs*100]
        }
        st.bar_chart(fractions_data, x="Component", y="Fraction (%)")
        
        # ISO Compliance
        st.subheader("🏛️ ISO Compliance")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Region", comp.iso_region.upper())
            status = "✅ Required" if comp.requires_llis else "⚪ Not Required"
            st.metric("LLIS Study", status)
        
        with col2:
            st.metric("VRT Profile", comp.voltage_ride_through.get("profile", "N/A"))
            harmonic_status = "✅ Compliant" if comp.harmonics.ieee_519_compliant else "❌ Non-Compliant"
            st.metric("IEEE 519", harmonic_status)
    
    def _render_export(self, st):
        """Render export options."""
        if not st.session_state.get("composition_calculated"):
            st.info("Calculate composition first in the Results tab")
            return
        
        st.subheader("📤 Export Engineering Data")
        
        config = self._current_config
        if config is None:
            return
        
        bus_number = st.number_input("PSS/e Bus Number", value=401001, step=1)
        
        if st.button("🔧 Generate Export Package"):
            export_pkg = self.manager.generate_export_package(
                config.site_id,
                bus_number=int(bus_number)
            )
            
            if export_pkg:
                st.session_state["export_package"] = export_pkg
                st.success("Export package generated!")
        
        # Show download buttons if package exists
        if "export_package" in st.session_state:
            pkg = st.session_state["export_package"]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.download_button(
                    "📥 PSS/e DYR File",
                    data=pkg.psse_dyr_content,
                    file_name=f"{pkg.site_id}_load_model.dyr",
                    mime="text/plain"
                )
            
            with col2:
                st.download_button(
                    "📥 ETAP JSON",
                    data=json.dumps(pkg.etap_json, indent=2),
                    file_name=f"{pkg.site_id}_etap_data.json",
                    mime="application/json"
                )
            
            with col3:
                st.download_button(
                    "📥 RAM JSON",
                    data=json.dumps(pkg.ram_json, indent=2),
                    file_name=f"{pkg.site_id}_ram_data.json",
                    mime="application/json"
                )


# =============================================================================
# SECTION 4: OPTIMIZER INTEGRATION FUNCTIONS
# =============================================================================

def create_pyomo_load_set(
    manager: LoadManager,
    site_ids: List[str]
) -> Tuple[Dict[str, Any], Dict[str, List[float]]]:
    """
    Create Pyomo parameter dictionaries for multiple sites.
    
    Used by design.py Stage 1 optimization.
    
    Args:
        manager: LoadManager with configured sites
        site_ids: List of site IDs to include
        
    Returns:
        Tuple of (parameter_dict, load_profiles_dict)
    """
    params = {}
    profiles = {}
    
    for site_id in site_ids:
        opt_input = manager.get_optimizer_parameters(site_id)
        if opt_input:
            params[site_id] = opt_input.to_pyomo_params()
            if opt_input.load_profile_multipliers:
                profiles[site_id] = opt_input.load_profile_multipliers
    
    return params, profiles


def get_aggregate_dr_capacity(manager: LoadManager, site_ids: List[str]) -> Dict[str, float]:
    """
    Calculate aggregate demand response capacity across sites.
    
    Used for grid services optimization.
    
    Args:
        manager: LoadManager with configured sites
        site_ids: List of site IDs to aggregate
        
    Returns:
        Dictionary with aggregate DR capacities by program type
    """
    totals = {
        "total_load_mw": 0.0,
        "economic_dr_mw": 0.0,
        "ers_30_mw": 0.0,
        "ers_10_mw": 0.0,
    }
    
    for site_id in site_ids:
        opt_input = manager.get_optimizer_parameters(site_id)
        if opt_input:
            totals["total_load_mw"] += opt_input.peak_load_mw
            totals["economic_dr_mw"] += opt_input.economic_dr_mw
            totals["ers_30_mw"] += opt_input.ers_30_mw
            totals["ers_10_mw"] += opt_input.ers_10_mw
    
    return totals


# =============================================================================
# SECTION 5: UTILITY FUNCTIONS
# =============================================================================

def validate_pue_for_cooling(cooling_type: str, pue: float) -> Tuple[bool, str]:
    """
    Validate PUE is within acceptable range for cooling type.
    
    Args:
        cooling_type: Cooling technology key
        pue: PUE value to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    if cooling_type not in COOLING_SPECS:
        return False, f"Unknown cooling type: {cooling_type}"
    
    pue_range = COOLING_SPECS[cooling_type]["pue_range"]
    
    if pue < pue_range[0]:
        return False, f"PUE {pue} is below minimum {pue_range[0]} for {cooling_type}"
    
    if pue > pue_range[1]:
        return False, f"PUE {pue} is above maximum {pue_range[1]} for {cooling_type}"
    
    return True, "OK"


def get_iso_threshold(iso_region: str) -> float:
    """Get large load interconnection threshold for ISO region."""
    if iso_region not in ISO_PROFILES:
        return 100.0  # Default
    return ISO_PROFILES[iso_region]["large_load_threshold_mw"]


def estimate_equipment_costs(composition: LoadComposition) -> Dict[str, float]:
    """
    Estimate equipment capital costs based on load composition.
    
    NOTE: These are rough order-of-magnitude estimates.
    
    Args:
        composition: Calculated load composition
        
    Returns:
        Dictionary of equipment type to estimated cost ($)
    """
    eq = composition.equipment
    
    # Unit costs (rough estimates, $/unit)
    UPS_COST_PER_KVA = 150  # $/kVA for large UPS
    CHILLER_COST_PER_MW = 500_000  # $/MW electrical
    CRAH_COST_PER_KW = 400  # $/kW
    PUMP_COST_PER_KW = 200  # $/kW
    
    costs = {
        "ups_total": eq.ups_count * eq.ups_rating_kva * UPS_COST_PER_KVA,
        "chiller_total": eq.chiller_count * eq.chiller_rating_mw * CHILLER_COST_PER_MW,
        "crah_total": eq.crah_count * eq.crah_rating_kw * CRAH_COST_PER_KW,
        "pump_total": eq.pump_count * eq.pump_rating_kw * PUMP_COST_PER_KW,
    }
    
    costs["total_mechanical_electrical"] = sum(costs.values())
    
    return costs


# =============================================================================
# SECTION 6: MAIN ENTRY POINT
# =============================================================================

def main():
    """
    Example usage and test of the wrapper module.
    """
    print("=" * 70)
    print("bvNexus Load Integration Wrapper - Test Run")
    print("=" * 70)
    
    # Create manager
    manager = LoadManager()
    
    # Add test site
    config = SiteLoadConfig(
        site_id="TEST_001",
        site_name="Test Datacenter",
        peak_load_mw=200,
        pue=1.3,
        cooling_type="rear_door_heat_exchanger",
        iso_region="ercot",
        pre_training_pct=30,
        fine_tuning_pct=20,
        batch_inference_pct=30,
        realtime_inference_pct=20,
    )
    
    composition = manager.add_site(config)
    
    print(f"\n✅ Site Added: {config.site_id}")
    print(f"   Total Load: {composition.total_mw:.1f} MW")
    print(f"   IT Load: {composition.it_load_mw:.1f} MW")
    print(f"   Cooling Load: {composition.cooling_load_mw:.1f} MW")
    
    # Get optimizer parameters
    opt_params = manager.get_optimizer_parameters("TEST_001")
    print(f"\n📊 Optimizer Parameters:")
    print(f"   DR Capacity: {opt_params.dr_capacity_mw:.1f} MW")
    print(f"   ERS-30 Eligible: {opt_params.ers_30_mw:.1f} MW")
    print(f"   Requires LLIS: {opt_params.requires_llis}")
    
    # Generate export package
    export_pkg = manager.generate_export_package("TEST_001", bus_number=401001)
    print(f"\n📤 Export Package Generated:")
    print(f"   PSS/e DYR: {len(export_pkg.psse_dyr_content)} chars")
    print(f"   ETAP JSON: {len(json.dumps(export_pkg.etap_json))} chars")
    print(f"   RAM JSON: {len(json.dumps(export_pkg.ram_json))} chars")
    
    # Estimate costs
    costs = estimate_equipment_costs(composition)
    print(f"\n💰 Estimated M&E Costs:")
    print(f"   UPS: ${costs['ups_total']:,.0f}")
    print(f"   Chillers: ${costs['chiller_total']:,.0f}")
    print(f"   Total M&E: ${costs['total_mechanical_electrical']:,.0f}")
    
    print("\n" + "=" * 70)
    print("✅ Wrapper test complete - ready for Antigravity integration")
    print("=" * 70)
    
    return manager, composition, export_pkg


if __name__ == "__main__":
    main()
