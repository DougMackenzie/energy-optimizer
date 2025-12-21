"""
Antigravity Energy Optimizer - Tests
Basic tests for core functionality
"""

import pytest
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.load_profile import LoadProfile, WorkloadMix
from app.models.equipment import RecipEngine, BESS, EquipmentType
from app.utils.calculations import (
    calculate_availability,
    calculate_capacity,
    calculate_nox,
)


class TestWorkloadMix:
    """Tests for WorkloadMix model"""
    
    def test_default_sums_to_one(self):
        mix = WorkloadMix()
        total = sum(mix.to_dict().values())
        assert abs(total - 1.0) < 0.01
    
    def test_training_focused_preset(self):
        mix = WorkloadMix.training_focused()
        assert mix.pre_training == 0.70
        total = sum(mix.to_dict().values())
        assert abs(total - 1.0) < 0.01
    
    def test_invalid_mix_raises(self):
        with pytest.raises(ValueError):
            WorkloadMix(pre_training=0.5, fine_tuning=0.5, batch_inference=0.5)


class TestLoadProfile:
    """Tests for LoadProfile model"""
    
    def test_total_facility_calculation(self):
        profile = LoadProfile(it_capacity_mw=160, design_pue=1.25)
        assert profile.total_facility_mw == 200.0
    
    def test_peak_facility_calculation(self):
        profile = LoadProfile(it_capacity_mw=160, pue_peak=1.35)
        assert profile.peak_facility_mw == 216.0
    
    def test_8760_generation(self):
        profile = LoadProfile(it_capacity_mw=160)
        load = profile.generate_8760()
        assert len(load) == 8760
        assert load.min() > 0
        assert load.max() < profile.peak_facility_mw * 1.5


class TestEquipment:
    """Tests for Equipment models"""
    
    def test_recip_engine_creation(self):
        engine = RecipEngine(
            id="test_engine",
            name="Test Engine",
            capacity_mw=18.8,
            efficiency_pct=48.0,
        )
        assert engine.type == EquipmentType.RECIP
        assert engine.capacity_mw == 18.8
    
    def test_recip_ramp_rate_conversion(self):
        engine = RecipEngine(
            id="test",
            name="Test",
            capacity_mw=18.8,
            ramp_rate_mw_min=3.0,
        )
        assert engine.ramp_rate_mw_s == 0.05
    
    def test_bess_usable_energy(self):
        bess = BESS(
            id="test_bess",
            name="Test BESS",
            energy_mwh=100,
            power_mw=25,
            dod_pct=80,
        )
        assert bess.usable_energy_mwh == 80.0


class TestCalculations:
    """Tests for calculation utilities"""
    
    def test_series_availability(self):
        avail = calculate_availability([0.99, 0.99, 0.99], "series")
        assert abs(avail - 0.970299) < 0.001
    
    def test_parallel_availability(self):
        avail = calculate_availability([0.90, 0.90], "parallel")
        assert abs(avail - 0.99) < 0.001
    
    def test_k_of_n_availability(self):
        # 5 of 6 with 97.5% each
        avail = calculate_availability([0.975] * 6, "k_of_n", k_of_n=(5, 6))
        assert avail > 0.99  # Should be very high with redundancy
    
    def test_capacity_calculation(self):
        equipment = [
            {"id": "engine", "capacity_mw": 18.8},
            {"id": "bess", "power_mw": 25},
        ]
        quantities = {"engine": 6, "bess": 1}
        
        total, n_minus_1 = calculate_capacity(equipment, quantities)
        assert abs(total - 137.8) < 0.1
        assert abs(n_minus_1 - 119.0) < 0.1  # Total minus largest (25)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
