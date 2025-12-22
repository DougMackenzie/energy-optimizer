"""
Constraint Validation Engine
Checks equipment configurations against site constraints
"""

from typing import Dict, List, Tuple, Any


class ConstraintValidator:
    """Validates equipment configurations against site constraints"""
    
    def __init__(self, site_constraints: Dict, site_details: Dict):
        self.constraints = site_constraints
        self.site = site_details
        self.violations = []
        self.warnings = []
    
    def validate_all(self, equipment_config: Dict) -> Tuple[bool, List[str], List[str]]:
        """
        Run all constraint checks
        
        Returns:
            (is_feasible, violations, warnings)
        """
        self.violations = []
        self.warnings = []
        
        # Run all validation checks
        self.check_air_permits(equipment_config)
        self.check_gas_supply(equipment_config)
        self.check_grid_capacity(equipment_config)
        self.check_land_area(equipment_config)
        self.check_reliability(equipment_config)
        
        is_feasible = len(self.violations) == 0
        
        return is_feasible, self.violations, self.warnings
    
    def check_air_permits(self, equipment_config: Dict) -> None:
        """Check air permit compliance (NOx, CO, VOC)"""
        
        # Calculate annual emissions
        # Assume equipment_config has format:
        # {
        #   'recip_engines': [{'capacity_mw': 18, 'capacity_factor': 0.7, 'nox_lb_mmbtu': 0.099, ...}],
        #   'gas_turbines': [...],
        # }
        
        total_nox_tpy = 0
        total_co_tpy = 0
        
        # Reciprocating Engines
        for engine in equipment_config.get('recip_engines', []):
            capacity_mw = engine.get('capacity_mw', 0)
            capacity_factor = engine.get('capacity_factor', 0.7)  # Default 70%
            heat_rate = engine.get('heat_rate_btu_kwh', 7700)
            nox_lb_mmbtu = engine.get('nox_lb_mmbtu', 0.099)
            co_lb_mmbtu = engine.get('co_lb_mmbtu', 0.015)
            
            # Annual fuel consumption (MMBtu/year)
            annual_fuel_mmbtu = capacity_mw * 1000 * capacity_factor * heat_rate * 8760 / 1_000_000
            
            # Annual emissions (tons/year)
            nox_tons = (annual_fuel_mmbtu * nox_lb_mmbtu) / 2000
            co_tons = (annual_fuel_mmbtu * co_lb_mmbtu) / 2000
            
            total_nox_tpy += nox_tons
            total_co_tpy += co_tons
        
        # Gas Turbines
        for turbine in equipment_config.get('gas_turbines', []):
            capacity_mw = turbine.get('capacity_mw', 0)
            capacity_factor = turbine.get('capacity_factor', 0.5)  # Lower CF for peaking
            heat_rate = turbine.get('heat_rate_btu_kwh', 8500)
            nox_lb_mmbtu = turbine.get('nox_lb_mmbtu', 0.099)
            co_lb_mmbtu = turbine.get('co_lb_mmbtu', 0.015)
            
            annual_fuel_mmbtu = capacity_mw * 1000 * capacity_factor * heat_rate * 8760 / 1_000_000
            
            nox_tons = (annual_fuel_mmbtu * nox_lb_mmbtu) / 2000
            co_tons = (annual_fuel_mmbtu * co_lb_mmbtu) / 2000
            
            total_nox_tpy += nox_tons
            total_co_tpy += co_tons
        
        # Check against limits
        nox_limit = self.constraints.get('NOx_Limit_tpy', 100)
        co_limit = self.constraints.get('CO_Limit_tpy', 250)
        
        if total_nox_tpy > nox_limit:
            self.violations.append(
                f"Air Permit: NOx emissions {total_nox_tpy:.1f} tpy exceeds limit of {nox_limit} tpy"
            )
        elif total_nox_tpy > nox_limit * 0.9:
            self.warnings.append(
                f"Air Permit: NOx emissions {total_nox_tpy:.1f} tpy approaching limit of {nox_limit} tpy"
            )
        
        if total_co_tpy > co_limit:
            self.violations.append(
                f"Air Permit: CO emissions {total_co_tpy:.1f} tpy exceeds limit of {co_limit} tpy"
            )
        elif total_co_tpy > co_limit * 0.9:
            self.warnings.append(
                f"Air Permit: CO emissions {total_co_tpy:.1f} tpy approaching limit of {co_limit} tpy"
            )
    
    def check_gas_supply(self, equipment_config: Dict) -> None:
        """Check natural gas supply capacity"""
        
        # Calculate peak gas demand (MCF/day)
        peak_gas_mcf_day = 0
        
        # Gas heat content: 1.037 MMBtu/MCF (industry standard)
        gas_hhv = 1.037
        
        # Reciprocating Engines
        for engine in equipment_config.get('recip_engines', []):
            capacity_mw = engine.get('capacity_mw', 0)
            heat_rate = engine.get('heat_rate_btu_kwh', 7700)
            
            # Peak fuel consumption (MMBtu/hr @ 100% load)
            peak_fuel_mmbtu_hr = capacity_mw * 1000 * heat_rate / 1_000_000
            
            # Convert to MCF/day (24 hours)
            peak_gas_mcf_day += (peak_fuel_mmbtu_hr * 24) / gas_hhv
        
        # Gas Turbines
        for turbine in equipment_config.get('gas_turbines', []):
            capacity_mw = turbine.get('capacity_mw', 0)
            heat_rate = turbine.get('heat_rate_btu_kwh', 8500)
            
            peak_fuel_mmbtu_hr = capacity_mw * 1000 * heat_rate / 1_000_000
            peak_gas_mcf_day += (peak_fuel_mmbtu_hr * 24) / gas_hhv
        
        # Check against available supply
        gas_supply = self.constraints.get('Gas_Supply_MCF_day', 0)
        
        if peak_gas_mcf_day > gas_supply:
            self.violations.append(
                f"Gas Supply: Peak demand {peak_gas_mcf_day:,.0f} MCF/day exceeds supply of {gas_supply:,.0f} MCF/day"
            )
        elif peak_gas_mcf_day > gas_supply * 0.9:
            self.warnings.append(
                f"Gas Supply: Peak demand {peak_gas_mcf_day:,.0f} MCF/day approaching supply limit of {gas_supply:,.0f} MCF/day"
            )
    
    def check_grid_capacity(self, equipment_config: Dict) -> None:
        """Check grid import capacity"""
        
        grid_import_mw = equipment_config.get('grid_import_mw', 0)
        grid_available = self.constraints.get('Grid_Available_MW', 0)
        
        if grid_import_mw > grid_available:
            self.violations.append(
                f"Grid Capacity: Import {grid_import_mw} MW exceeds available {grid_available} MW"
            )
    
    def check_land_area(self, equipment_config: Dict) -> None:
        """Check land area for solar deployment"""
        
        solar_mw_dc = equipment_config.get('solar_mw_dc', 0)
        
        if solar_mw_dc > 0:
            # Single-axis tracker: ~4.25 acres/MW DC
            required_acres = solar_mw_dc * 4.25
            available_acres = self.constraints.get('Available_Land_Acres', 0)
            
            if required_acres > available_acres:
                self.violations.append(
                    f"Land Area: Solar requires {required_acres:.1f} acres, only {available_acres:.1f} acres available"
                )
            elif required_acres > available_acres * 0.9:
                self.warnings.append(
                    f"Land Area: Solar using {required_acres:.1f} of {available_acres:.1f} acres available"
                )
    
    def check_reliability(self, equipment_config: Dict) -> None:
        """Check N-1 reliability requirement"""
        
        n1_required = self.constraints.get('N_Minus_1_Required', 'No')
        
        if n1_required == 'Yes':
            # Calculate total capacity and largest unit
            all_units = []
            
            for engine in equipment_config.get('recip_engines', []):
                all_units.append(engine.get('capacity_mw', 0))
            
            for turbine in equipment_config.get('gas_turbines', []):
                all_units.append(turbine.get('capacity_mw', 0))
            
            if all_units:
                total_capacity = sum(all_units)
                largest_unit = max(all_units)
                firm_capacity = total_capacity - largest_unit
                
                required_mw = self.site.get('Total_Facility_MW', 0)
                
                if firm_capacity < required_mw:
                    self.violations.append(
                        f"N-1 Reliability: Firm capacity {firm_capacity:.1f} MW insufficient for {required_mw} MW load"
                    )
                elif firm_capacity < required_mw * 1.05:
                    self.warnings.append(
                        f"N-1 Reliability: Firm capacity {firm_capacity:.1f} MW has minimal margin for {required_mw} MW load"
                    )


def validate_configuration(
    site: Dict,
    constraints: Dict,
    equipment_config: Dict
) -> Tuple[bool, List[str], List[str], Dict]:
    """
    Validate equipment configuration against site constraints
    
    Args:
        site: Site details dict
        constraints: Site constraints dict
        equipment_config: Equipment configuration with capacities
    
    Returns:
        (is_feasible, violations, warnings, metrics)
    """
    
    validator = ConstraintValidator(constraints, site)
    is_feasible, violations, warnings = validator.validate_all(equipment_config)
    
    # Calculate metrics
    metrics = calculate_metrics(equipment_config)
    
    return is_feasible, violations, warnings, metrics


def calculate_metrics(equipment_config: Dict) -> Dict:
    """Calculate key metrics for configuration"""
    
    total_capacity = 0
    total_capex = 0
    
    # Reciprocating Engines
    for engine in equipment_config.get('recip_engines', []):
        cap = engine.get('capacity_mw', 0)
        capex_per_kw = engine.get('capex_per_kw', 1650)
        total_capacity += cap
        total_capex += cap * 1000 * capex_per_kw
    
    # Gas Turbines
    for turbine in equipment_config.get('gas_turbines', []):
        cap = turbine.get('capacity_mw', 0)
        capex_per_kw = turbine.get('capex_per_kw', 1300)
        total_capacity += cap
        total_capex += cap * 1000 * capex_per_kw
    
    # BESS
    for bess in equipment_config.get('bess', []):
        energy_mwh = bess.get('energy_mwh', 0)
        capex_per_kwh = bess.get('capex_per_kwh', 236)
        total_capex += energy_mwh * 1000 * capex_per_kwh
    
    # Solar
    solar_mw_dc = equipment_config.get('solar_mw_dc', 0)
    solar_capex_per_w = equipment_config.get('solar_capex_per_w', 0.95)
    total_capex += solar_mw_dc * 1_000_000 * solar_capex_per_w
    
    return {
        'total_capacity_mw': total_capacity,
        'total_capex_m': total_capex / 1_000_000,
        'solar_mw_dc': solar_mw_dc
    }
