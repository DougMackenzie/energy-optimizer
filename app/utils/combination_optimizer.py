"""
Combination Optimizer - Two-level hierarchical optimization

Level 1: Which equipment types to use (discrete combinatorial choice)
Level 2: How much of each type per year (continuous temporal optimization)

This solves the search space explosion problem by testing equipment
combinations separately rather than all types simultaneously.
"""

from typing import List, Dict, Tuple
from itertools import product
import numpy as np
from app.utils.phased_optimizer import PhasedDeploymentOptimizer


class CombinationOptimizer:
    """
    Hierarchical optimizer that tests equipment type combinations.
    
    For each viable combination of equipment types:
    1. Enable only that combination
    2. Run temporal optimization (deployment schedule over 8 years)
    3. Track feasibility and performance
    4. Return best combination
    """
    
    def __init__(self, site: Dict, scenario: Dict, equipment_data: Dict, constraints: Dict):
        self.site = site
        self.scenario = scenario
        self.equipment_data = equipment_data
        self.constraints = constraints
        
        # Get equipment types available in scenario
        self.available_recip = scenario.get('Recip_Enabled', True)
        self.available_turbine = scenario.get('Turbine_Enabled', True)
        self.available_bess = scenario.get('BESS_Enabled', True)
        self.available_solar = scenario.get('Solar_Enabled', True)
        self.available_grid = scenario.get('Grid_Enabled', False)
    
    def generate_combinations(self) -> List[Dict]:
        """
        Generate all reasonable equipment combinations to test.
        
        Returns list of combination dicts with equipment enable/disable flags.
        """
        combinations = []
        
        if not self.available_grid:
            # BTM Only scenarios - test comprehensive combinations
            # Start with single technologies (baseline understanding)
            
            # 1. Pure firm power (gas-fired)
            if self.available_recip:
                combinations.append({
                    'name': 'Recips Only',
                    'recip': True, 'turbine': False, 'bess': False, 'solar': False, 'grid': False
                })
            
            if self.available_turbine:
                combinations.append({
                    'name': 'Turbines Only',
                    'recip': False, 'turbine': True, 'bess': False, 'solar': False, 'grid': False
                })
            
            # 2. Firm power + storage (high-value pairings)
            if self.available_recip and self.available_bess:
                combinations.append({
                    'name': 'Recips + BESS',
                    'recip': True, 'turbine': False, 'bess': True, 'solar': False, 'grid': False
                })
            
            if self.available_turbine and self.available_bess:
                combinations.append({
                    'name': 'Turbines + BESS',
                    'recip': False, 'turbine': True, 'bess': True, 'solar': False, 'grid': False
                })
            
            # 3. Hybrid firm power (recips + turbines)
            if self.available_recip and self.available_turbine:
                combinations.append({
                    'name': 'Recips + Turbines',
                    'recip': True, 'turbine': True, 'bess': False, 'solar': False, 'grid': False
                })
                
                # With BESS for optimal dispatch
                if self.available_bess:
                    combinations.append({
                        'name': 'Recips + Turbines + BESS',
                        'recip': True, 'turbine': True, 'bess': True, 'solar': False, 'grid': False
                    })
            
            # 4. Renewable + storage
            if self.available_solar and self.available_bess:
                combinations.append({
                    'name': 'Solar + BESS',
                    'recip': False, 'turbine': False, 'bess': True, 'solar': True, 'grid': False
                })
            
            # 5. Firm + renewables (optimal hybrid)
            if self.available_recip and self.available_solar:
                combinations.append({
                    'name': 'Recips + Solar',
                    'recip': True, 'turbine': False, 'bess': False, 'solar': True, 'grid': False
                })
                
                if self.available_bess:
                    combinations.append({
                        'name': 'Recips + Solar + BESS',
                        'recip': True, 'turbine': False, 'bess': True, 'solar': True, 'grid': False
                    })
            
            if self.available_turbine and self.available_solar:
                combinations.append({
                    'name': 'Turbines + Solar',
                    'recip': False, 'turbine': True, 'bess': False, 'solar': True, 'grid': False
                })
                
                if self.available_bess:
                    combinations.append({
                        'name': 'Turbines + Solar + BESS',
                        'recip': False, 'turbine': True, 'bess': True, 'solar': True, 'grid': False
                    })
            
            # 6. Full BTM stack (everything available)
            if all([self.available_recip, self.available_turbine, self.available_bess, self.available_solar]):
                combinations.append({
                    'name': 'All BTM Technologies',
                    'recip': True, 'turbine': True, 'bess': True, 'solar': True, 'grid': False
                })
        
        else:
            # Grid-inclusive scenarios - comprehensive testing
            # 1. Pure grid
            combinations.append({
                'name': 'Grid Only',
                'recip': False, 'turbine': False, 'bess': False, 'solar': False, 'grid': True
            })
            
            # 2. Simple BTM bridges
            if self.available_recip:
                combinations.append({
                    'name': 'Recips + Grid',
                    'recip': True, 'turbine': False, 'bess': False, 'solar': False, 'grid': True
                })
            
            if self.available_turbine:
                combinations.append({
                    'name': 'Turbines + Grid',
                    'recip': False, 'turbine': True, 'bess': False, 'solar': False, 'grid': True
                })
            
            # 3. Firm + BESS + grid
            if self.available_recip and self.available_bess:
                combinations.append({
                    'name': 'Recips + BESS + Grid',
                    'recip': True, 'turbine': False, 'bess': True, 'solar': False, 'grid': True
                })
            
            if self.available_turbine and self.available_bess:
                combinations.append({
                    'name': 'Turbines + BESS + Grid',
                    'recip': False, 'turbine': True, 'bess': True, 'solar': False, 'grid': True
                })
            
            # 4. Hybrid firm + grid
            if self.available_recip and self.available_turbine:
                combinations.append({
                    'name': 'Recips + Turbines + Grid',
                    'recip': True, 'turbine': True, 'bess': False, 'solar': False, 'grid': True
                })
                
                if self.available_bess:
                    combinations.append({
                        'name': 'Recips + Turbines + BESS + Grid',
                        'recip': True, 'turbine': True, 'bess': True, 'solar': False, 'grid': True
                    })
            
            # 5. Solar + Grid
            if self.available_solar and self.available_bess:
                combinations.append({
                    'name': 'Solar + BESS + Grid',
                    'recip': False, 'turbine': False, 'bess': True, 'solar': True, 'grid': True
                })
            
            # 6. Firm + Solar + Grid
            if self.available_recip and self.available_solar and self.available_bess:
                combinations.append({
                    'name': 'Recips + Solar + BESS + Grid',
                    'recip': True, 'turbine': False, 'bess': True, 'solar': True, 'grid': True
                })
            
            if self.available_turbine and self.available_solar and self.available_bess:
                combinations.append({
                    'name': 'Turbines + Solar + BESS + Grid',
                    'recip': False, 'turbine': True, 'bess': True, 'solar': True, 'grid': True
                })
            
            # 7. Full stack
            if all([self.available_recip, self.available_turbine, self.available_bess, self.available_solar]):
                combinations.append({
                    'name': 'All Technologies + Grid',
                    'recip': True, 'turbine': True, 'bess': True, 'solar': True, 'grid': True
                })
        
        return combinations
    
    def optimize_combination(self, combo: Dict, seed_deployments: List[Dict] = None) -> Tuple[Dict, float, List[str], float, int]:
        """
        Optimize deployment schedule for a specific equipment combination.
        
        Args:
            combo: Equipment combination dict with enable/disable flags
            seed_deployments: Optional list of successful deployments from simpler combinations
        
        Returns:
            deployment: Deployment schedule by year
            lcoe: Lifecycle LCOE ($/MWh)
            violations: List of constraint violation messages
            total_power_delivered: Total MW-years delivered over planning horizon
            critical_path_months: Longest equipment lead time (deployment speed)
        """
        # Create modified scenario with only this combination enabled
        combo_scenario = self.scenario.copy()
        combo_scenario['Recip_Enabled'] = combo['recip']
        combo_scenario['Turbine_Enabled'] = combo['turbine']
        combo_scenario['BESS_Enabled'] = combo['bess']
        combo_scenario['Solar_Enabled'] = combo['solar']
        combo_scenario['Grid_Enabled'] = combo['grid']
        
        # Get load trajectory - 10 years
        load_trajectory = self.site.get('load_trajectory', {
            2026: 0, 2027: 0, 2028: 150, 2029: 300, 2030: 450, 2031: 600,
            2032: 600, 2033: 600, 2034: 600, 2035: 600
        })
        
        # Run phased optimizer for this specific combination
        optimizer = PhasedDeploymentOptimizer(
            site=self.site,
            equipment_data=self.equipment_data,
            constraints=self.constraints,
            load_trajectory=load_trajectory,
            scenario=combo_scenario
        )
        
        # Optimize temporal deployment with seeds
        deployment, lcoe, violations = optimizer.optimize(seed_deployments=seed_deployments)
        
        # Calculate total power delivered over planning horizon
        total_power = 0
        for year in optimizer.years:
            capacity = optimizer.get_cumulative_capacity_mw(deployment, year)
            target = load_trajectory.get(year, 0)
            delivered = min(capacity, target)
            total_power += delivered
        
        # Calculate critical path (longest lead time of enabled equipment)
        critical_path_months = 0
        lead_times = {
            'recip': 18, 'turbine': 24, 'bess': 12, 'solar': 15, 'grid': combo_scenario.get('Grid_Timeline_Months', 96)
        }
        for equip_type, enabled in combo.items():
            if enabled and equip_type in lead_times:
                critical_path_months = max(critical_path_months, lead_times[equip_type])
        
        return deployment, lcoe, violations, total_power, critical_path_months
    
    def optimize_all(self) -> List[Dict]:
        """
        Test all equipment combinations and return ranked results.
        
        Returns list of results sorted by:
        1. Feasibility (feasible first)
        2. Total power delivered (descending)
        3. LCOE (ascending)
        """
        combinations = self.generate_combinations()
        
        # Sort combinations by complexity (number of enabled technologies)
        # This ensures we run simpler combinations first to seed complex ones
        combinations.sort(key=lambda c: sum([c.get('recip',0), c.get('turbine',0), c.get('bess',0), c.get('solar',0), c.get('grid',0)]))
        
        results = []
        feasible_deployments = []  # Store feasible deployments to seed future runs
        
        print(f"\n{'='*80}")
        print(f"🔍 COMBINATION OPTIMIZER - Testing {len(combinations)} equipment combinations")
        print(f"{'='*80}")
        
        for idx, combo in enumerate(combinations):
            combo_name = combo['name']
            
            print(f"\n[{idx+1}/{len(combinations)}] Testing: {combo_name}")
            print(f"  Equipment: ", end="")
            enabled_types = [k.capitalize() for k, v in combo.items() if k != 'name' and v]
            print(" + ".join(enabled_types))
            
            try:
                # Pass all previously found feasible deployments as seeds
                # The optimizer will automatically map them to the current problem
                deployment, lcoe, violations, power, critical_path = self.optimize_combination(combo, seed_deployments=feasible_deployments)
                
                is_feasible = len(violations) == 0
                
                if is_feasible:
                    # Store this feasible deployment to seed future complex runs
                    feasible_deployments.append(deployment)
                
                result = {
                    'combination': combo,
                    'combination_name': combo_name,
                    'deployment': deployment,
                    'lcoe': lcoe,
                    'violations': violations,
                    'total_power_delivered': power,
                    'critical_path_months': critical_path,
                    'feasible': is_feasible
                }
                
                if is_feasible:
                    print(f"  ✅ FEASIBLE: {power:.0f} MW-years, LCOE ${lcoe:.2f}/MWh, Timeline {critical_path} months")
                else:
                    print(f"  ❌ INFEASIBLE: {len(violations)} violations")
                    for v in violations[:3]:  # Show first 3 violations
                        print(f"      - {v}")
                
                results.append(result)
            
            except Exception as e:
                print(f"  ⚠️ ERROR: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        # Sort results: feasible first, then by power delivered, then by LCOE
        feasible = [r for r in results if r['feasible']]
        infeasible = [r for r in results if not r['feasible']]
        
        feasible.sort(key=lambda x: (-x['total_power_delivered'], x['lcoe']))
        infeasible.sort(key=lambda x: len(x['violations']))
        
        ranked_results = feasible + infeasible
        
        # Summary
        print(f"\n{'='*80}")
        print(f"📊 COMBINATION OPTIMIZER RESULTS")
        print(f"{'='*80}")
        print(f"Feasible combinations: {len(feasible)}/{len(results)}")
        
        if feasible:
            best = feasible[0]
            print(f"\n🏆 BEST COMBINATION: {best['combination_name']}")
            print(f"  Power delivered: {best['total_power_delivered']:.0f} MW-years")
            print(f"  LCOE: ${best['lcoe']:.2f}/MWh")
            print(f"  Timeline: {best['critical_path_months']} months")
        else:
            print(f"\n❌ NO FEASIBLE COMBINATIONS FOUND")
            print(f"All {len(results)} combinations violated constraints")
            if infeasible:
                print(f"\nLeast violations: {infeasible[0]['combination_name']} ({len(infeasible[0]['violations'])} violations)")
        
        return ranked_results
