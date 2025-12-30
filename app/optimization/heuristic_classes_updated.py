"""
Updated Problem Classes 2-5 with Annual Energy Stack Integration
Copy these into heuristic_optimizer.py to replace existing classes
"""

class BrownfieldHeuristic(HeuristicOptimizer):
    """Problem 2: Brownfield - Max load within LCOE ceiling
    
    Hierarchical Objective:
    1. LCOE ≤ ceiling (hard constraint)
    2. Maximize expansion capacity (MW added)
    """
    
    def __init__(self, *args, existing_equipment: Dict = None, lcoe_threshold: float = 120, **kwargs):
        super().__init__(*args, **kwargs)
        self.existing_equipment = existing_equipment or {}
        self.lcoe_threshold = lcoe_threshold
    
    def optimize(self) -> HeuristicResult:
        start_time = time.time()
        existing_mw = sum([
            self.existing_equipment.get('recip_mw', 0),
            self.existing_equipment.get('turbine_mw', 0),
            self.existing_equipment.get('grid_mw', 0)
        ])
        existing_lcoe = self.existing_equipment.get('existing_lcoe', 80)
        lcoe_headroom = self.lcoe_threshold - existing_lcoe
        
        if lcoe_headroom <= 0:
            return HeuristicResult(
                feasible=False, objective_value=0, lcoe=existing_lcoe, capex_total=0, opex_annual=0,
                equipment_config={}, dispatch_summary={'max_expansion_mw': 0}, constraint_status={},
                violations=['LCOE ceiling already reached'], timeline_months=0, shadow_prices={},
                solve_time_seconds=time.time() - start_time, warnings=['No expansion possible'],
            )
        
        # Use annual stack for multi-year scenarios
        if len(self.years) > 1:
            annual_result = self.optimize_annual_energy_stack()
            
            # Check LCOE ceiling constraint
            if annual_result['blended_lcoe'] > self.lcoe_threshold:
                feasible = False
                warnings = [f"Blended LCOE ${annual_result['blended_lcoe']:.1f}/MWh exceeds ceiling ${self.lcoe_threshold:.1f}/MWh"]
            else:
                feasible = True
                warnings = []
            
            equipment = annual_result['final_equipment']
            lcoe = annual_result['blended_lcoe']
            max_expansion_mw = equipment.get('total_capacity_mw', 0) - existing_mw
            
            final_year = max(annual_result['annual_stack'].keys())
            final_data = annual_result['annual_stack'][final_year]
            unserved_mwh = final_data['unserved_mwh']
            unserved_pct = final_data['unserved_pct']
            energy_delivered = final_data['energy_delivered_mwh']
        else:
            # Single year optimization
            new_equipment = self.size_equipment_to_load(
                target_mw=min(self.peak_load * 0.5, self.peak_load - existing_mw),
                require_n1=False,
            )
            equipment = {**self.existing_equipment, **new_equipment}
            annual_energy_mwh = self.peak_load * 8760 * 0.85
            lcoe, lcoe_details = self.calculate_lcoe(equipment, annual_energy_mwh)
            
            feasible = lcoe <= self.lcoe_threshold
            warnings = lcoe_details.get('warnings', [])
            max_expansion_mw = new_equipment.get('total_capacity_mw', 0)
            unserved_mwh = lcoe_details.get('unserved_energy_mwh', 0)
            unserved_pct = lcoe_details.get('unserved_energy_pct', 0)
            energy_delivered = lcoe_details.get('energy_delivered_mwh', 0)
        
        capex = self.calculate_capex(equipment)
        opex = self.calculate_annual_opex(equipment)
        constraint_status, violations, constraint_analysis = self.check_constraints(equipment)
        
        return HeuristicResult(
            feasible=feasible and len(violations) == 0,
            objective_value=max_expansion_mw,  # Maximize expansion
            lcoe=lcoe,
            capex_total=capex,
            opex_annual=opex,
            equipment_config=equipment,
            dispatch_summary={
                'max_expansion_mw': max_expansion_mw,
                'blended_lcoe': lcoe,
                'existing_mw': existing_mw,
                'lcoe_threshold': self.lcoe_threshold,
            },
            constraint_status=constraint_status,
            violations=violations,
            timeline_months=self.calculate_timeline(equipment),
            shadow_prices={},
            solve_time_seconds=time.time() - start_time,
            warnings=warnings,
            unserved_energy_mwh=unserved_mwh,
            unserved_energy_pct=unserved_pct,
            energy_delivered_mwh=energy_delivered,
            constraint_utilization=constraint_analysis.get('utilization', {}),
            binding_constraint=constraint_analysis.get('binding', ''),
        )


class LandDevHeuristic(HeuristicOptimizer):
    """Problem 3: Land Development - Max capacity by flexibility scenario
    
    Hierarchical Objective:
    1. Respect constraints (NOx, Gas, Land hard limits)
    2. Maximize firm capacity that can be built
    3. Analyze across workload flexibility scenarios
    """
    
    def optimize(self) -> HeuristicResult:
        start_time = time.time()
        flex_scenarios = [0.0, 0.15, 0.30, 0.50]
        results_matrix = {}
        constraint_limits = self._calculate_constraint_limits()
        
        max_firm_mw = min(
            constraint_limits.get('max_thermal_mw_from_nox', float('inf')),
            constraint_limits.get('max_thermal_mw_from_gas', float('inf')),
            constraint_limits.get('max_thermal_mw_from_land', float('inf')),
        )
        
        binding = 'nox' if max_firm_mw == constraint_limits.get('max_thermal_mw_from_nox') else \
                  'gas' if max_firm_mw == constraint_limits.get('max_thermal_mw_from_gas') else 'land'
        
        # Run scenario for each flexibility level
        for flex in flex_scenarios:
            alignment_factor = 0.7
            load_max = max_firm_mw / (1 - flex * alignment_factor) if flex > 0 else max_firm_mw
            equipment = self.size_equipment_to_load(max_firm_mw, require_n1=False)
            lcoe, _ = self.calculate_lcoe(equipment, load_max * 8760 * 0.85)
            results_matrix[f'{int(flex*100)}%'] = {
                'load_max_mw': load_max,
                'firm_capacity_mw': max_firm_mw,
                'lcoe': lcoe,
                'binding_constraint': binding,
            }
        
        equipment = self.size_equipment_to_load(max_firm_mw, require_n1=False)
        lcoe, lcoe_details = self.calculate_lcoe(equipment)
        capex = self.calculate_capex(equipment)
        opex = self.calculate_annual_opex(equipment)
        constraint_status, violations, constraint_analysis = self.check_constraints(equipment)
        
        return HeuristicResult(
            feasible=len(violations) == 0,
            objective_value=max_firm_mw,  # Maximize capacity
            lcoe=lcoe,
            capex_total=capex,
            opex_annual=opex,
            equipment_config=equipment,
            dispatch_summary={
                'power_potential_matrix': results_matrix,
                'binding_constraint': binding,
                'max_firm_capacity_mw': max_firm_mw
            },
            constraint_status=constraint_status,
            violations=violations,
            timeline_months=self.calculate_timeline(equipment),
            shadow_prices={},
            solve_time_seconds=time.time() - start_time,
            warnings=lcoe_details.get('warnings', []),
            constraint_utilization=constraint_analysis.get('utilization', {}),
            binding_constraint=binding,
        )


class GridServicesHeuristic(HeuristicOptimizer):
    """Problem 4: Grid Services - Max DR revenue
    
    Hierarchical Objective:
    1. Size equipment for base load
    2. Calculate flexible MW from workload mix
    3. Maximize DR revenue (NOT minimize LCOE!)
    """
    
    def __init__(self, *args, workload_mix: Dict = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.workload_mix = workload_mix or {
            'pre_training': 0.40, 'fine_tuning': 0.15,
            'batch_inference': 0.20, 'realtime_inference': 0.15, 'cloud_hpc': 0.10
        }
    
    def optimize(self) -> HeuristicResult:
        start_time = time.time()
        
        # Calculate flexible MW from workload mix        
        total_flex_mw = 0
        flex_by_workload = {}
        for workload, share in self.workload_mix.items():
            flex_params = WORKLOAD_FLEXIBILITY.get(workload, {'flexibility_pct': 0})
            flex_mw = self.peak_load * share * flex_params.get('flexibility_pct', 0)
            flex_by_workload[workload] = flex_mw
            total_flex_mw += flex_mw
        
        # Size equipment (use annual stack if multi-year)
        if len(self.years) > 1:
            annual_result = self.optimize_annual_energy_stack()
            equipment = annual_result['final_equipment']
            lcoe = annual_result['blended_lcoe']
        else:
            equipment = self.size_equipment_to_load(self.peak_load)
            lcoe, _ = self.calculate_lcoe(equipment)
        
        # Calculate DR service revenue (SEPARATE from LCOE!)
        service_revenue = {}
        total_revenue = 0
        for service_id, service_params in DR_SERVICES.items():
            eligible_mw = total_flex_mw * 0.8
            if eligible_mw >= service_params.get('min_capacity_mw', 0):
                availability_revenue = eligible_mw * service_params.get('payment_mw_hr', 0) * 8760 if 'payment_mw_hr' in service_params else \
                                       eligible_mw * 1000 * service_params.get('payment_kw_yr', 0) if 'payment_kw_yr' in service_params else 0
                activation_revenue = eligible_mw * service_params.get('expected_hours_yr', 0) * service_params.get('activation_mwh', 0)
                service_revenue[service_id] = {'eligible_mw': eligible_mw, 'total_revenue': availability_revenue + activation_revenue}
                total_revenue += availability_revenue + activation_revenue
        
        return HeuristicResult(
            feasible=True,
            objective_value=total_revenue,  # Maximize DR revenue!
            lcoe=lcoe,
            capex_total=0,
            opex_annual=0,
            equipment_config=equipment,
            dispatch_summary={
                'total_flex_mw': total_flex_mw,
                'flex_by_workload': flex_by_workload,
                'service_revenue': service_revenue,
                'total_annual_revenue': total_revenue
            },
            constraint_status={},
            violations=[],
            timeline_months=0,
            shadow_prices={},
            solve_time_seconds=time.time() - start_time,
            warnings=[],
        )


class BridgePowerHeuristic(HeuristicOptimizer):
    """Problem 5: Bridge Power - Min NPV of transition
    
    Hierarchical Objective:
    1. Meet load until grid arrives (month X)
    2. Minimize NPV of total transition cost
    3. Compare: rental vs purchase vs hybrid
    """
    
    def __init__(self, *args, grid_available_month: int = 60, **kwargs):
        super().__init__(*args, **kwargs)
        self.grid_available_month = grid_available_month
    
    def optimize(self) -> HeuristicResult:
        start_time = time.time()
        monthly_rate = self.economics.get('discount_rate', 0.08) / 12
        scenarios = {}
        
        # Scenario 1: All rental until grid
        rental_cost = self.equipment.get('rental', {}).get('rental_cost_kw_month', 50)
        rental_npv = sum(self.peak_load * 1000 * rental_cost / (1 + monthly_rate) ** m for m in range(self.grid_available_month))
        scenarios['all_rental'] = rental_npv
        
        # Scenario 2: All purchase until grid
        purchase_equipment = self.size_equipment_to_load(self.peak_load)
        purchase_capex = self.calculate_capex(purchase_equipment)
        residual_value = purchase_capex * self.economics.get('residual_value_pct', 0.10)
        purchase_opex_monthly = self.calculate_annual_opex(purchase_equipment) / 12
        purchase_npv = purchase_capex + sum(purchase_opex_monthly / (1 + monthly_rate) ** m for m in range(self.grid_available_month))
        purchase_npv -= residual_value / (1 + monthly_rate) ** self.grid_available_month
        scenarios['all_purchase'] = purchase_npv
        
        # Scenario 3: Hybrid
        crossover_months = (purchase_capex - residual_value) / (rental_cost * self.peak_load * 1000 - purchase_opex_monthly) \
                           if (rental_cost * self.peak_load * 1000 - purchase_opex_monthly) > 0 else 999
        scenarios['hybrid'] = min(rental_npv, purchase_npv)
        
        best_scenario = min(scenarios, key=scenarios.get)
        best_npv = scenarios[best_scenario]
        
        return HeuristicResult(
            feasible=True,
            objective_value=best_npv,  # Minimize NPV
            lcoe=0,
            capex_total=purchase_capex if best_scenario == 'all_purchase' else 0,
            opex_annual=self.calculate_annual_opex(purchase_equipment) if best_scenario != 'all_rental' else 0,
            equipment_config=purchase_equipment,
            dispatch_summary={
                'scenarios': scenarios,
                'recommended': best_scenario,
                'npv': best_npv,
                'crossover_months': crossover_months,
                'grid_available_month': self.grid_available_month
            },
            constraint_status={},
            violations=[],
            timeline_months=self.grid_available_month,
            shadow_prices={},
            solve_time_seconds=time.time() - start_time,
            warnings=["Transition timing is indicative only"],
        )


def create_heuristic_optimizer(problem_type: int, **kwargs) -> HeuristicOptimizer:
    """Factory function to create appropriate heuristic optimizer."""
    optimizers = {1: GreenFieldHeuristic, 2: BrownfieldHeuristic, 3: LandDevHeuristic,
                  4: GridServicesHeuristic, 5: BridgePowerHeuristic}
    if problem_type not in optimizers:
        raise ValueError(f"Unknown problem type: {problem_type}")
    return optimizers[problem_type](**kwargs)
