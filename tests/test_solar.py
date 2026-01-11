"""
Unit tests for solar energy calculations.
"""

import pytest
import numpy as np
from src.solar import (
    calculate_solar_potential,
    calculate_roi,
    calculate_payback_period
)


# =============================================================================
# Solar Potential Tests
# =============================================================================

def test_calculate_solar_potential_basic():
    """Test basic solar potential calculation."""
    area = 100  # m²
    irradiance = 1000  # kWh/m²/year
    efficiency = 0.18  # 18%
    shading = 0.0  # No shading
    
    energy = calculate_solar_potential(area, irradiance, efficiency, shading)
    
    # E = 100 * 1000 * 0.18 * (1 - 0) = 18,000 kWh
    assert energy == pytest.approx(18000.0, rel=1e-2)


def test_calculate_solar_potential_with_shading():
    """Test solar potential with shading factor."""
    area = 100
    irradiance = 1000
    efficiency = 0.18
    shading = 0.3  # 30% shading
    
    energy = calculate_solar_potential(area, irradiance, efficiency, shading)
    
    # E = 100 * 1000 * 0.18 * (1 - 0.3) = 12,600 kWh
    assert energy == pytest.approx(12600.0, rel=1e-2)


def test_calculate_solar_potential_high_shading():
    """Test solar potential with high shading."""
    area = 100
    irradiance = 1000
    efficiency = 0.18
    shading = 0.8  # 80% shading
    
    energy = calculate_solar_potential(area, irradiance, efficiency, shading)
    
    # E = 100 * 1000 * 0.18 * (1 - 0.8) = 3,600 kWh
    assert energy == pytest.approx(3600.0, rel=1e-2)


def test_calculate_solar_potential_zero_area():
    """Test with zero roof area."""
    energy = calculate_solar_potential(0, 1000, 0.18, 0)
    assert energy == 0.0


def test_calculate_solar_potential_zero_irradiance():
    """Test with zero irradiance."""
    energy = calculate_solar_potential(100, 0, 0.18, 0)
    assert energy == 0.0


def test_calculate_solar_potential_negative_area():
    """Test with negative area."""
    energy = calculate_solar_potential(-100, 1000, 0.18, 0)
    assert energy == 0.0


def test_calculate_solar_potential_invalid_shading():
    """Test with invalid shading factor."""
    with pytest.raises(ValueError):
        calculate_solar_potential(100, 1000, 0.18, 1.5)  # Shading > 1
    
    with pytest.raises(ValueError):
        calculate_solar_potential(100, 1000, 0.18, -0.1)  # Shading < 0


def test_calculate_solar_potential_various_efficiencies():
    """Test with various panel efficiencies."""
    area = 100
    irradiance = 1000
    shading = 0.0
    
    # Test different efficiency levels
    efficiencies = [0.15, 0.18, 0.20, 0.22]  # 15% to 22%
    
    for eff in efficiencies:
        energy = calculate_solar_potential(area, irradiance, eff, shading)
        expected = area * irradiance * eff
        assert energy == pytest.approx(expected, rel=1e-2)


def test_calculate_solar_potential_realistic_amsterdam():
    """Test with realistic Amsterdam values."""
    area = 150  # m²
    irradiance = 1050  # kWh/m²/year (typical for Amsterdam)
    efficiency = 0.18
    shading = 0.15  # 15% shading
    
    energy = calculate_solar_potential(area, irradiance, efficiency, shading)
    
    # E = 150 * 1050 * 0.18 * 0.85 = 24,123.75 kWh
    assert energy == pytest.approx(24123.75, rel=1e-2)


# =============================================================================
# ROI Tests
# =============================================================================

def test_calculate_roi():
    """Test ROI calculation."""
    energy_kwh = 18000
    energy_price = 0.25  # €0.25 per kWh
    cost_per_m2 = 200
    area = 100
    
    roi = calculate_roi(energy_kwh, energy_price, cost_per_m2, area)
    
    # Annual revenue = 18000 * 0.25 = 4500
    # Cost = 100 * 200 = 20000
    # ROI = (4500 - 20000) / 20000 = -77.5%
    assert roi == pytest.approx(-77.5, rel=1e-2)


def test_calculate_roi_positive():
    """Test ROI calculation with positive return."""
    energy_kwh = 100000  # Very high energy
    energy_price = 0.25
    cost_per_m2 = 200
    area = 100
    
    roi = calculate_roi(energy_kwh, energy_price, cost_per_m2, area)
    
    # Annual revenue = 100000 * 0.25 = 25000
    # Cost = 100 * 200 = 20000
    # ROI = (25000 - 20000) / 20000 = 25%
    assert roi == pytest.approx(25.0, rel=1e-2)


def test_calculate_roi_zero_energy():
    """Test ROI with zero energy production."""
    roi = calculate_roi(0, 0.25, 200, 100)
    # Should return -100% (total loss)
    assert roi == pytest.approx(-100.0, rel=1e-2)


def test_calculate_roi_different_prices():
    """Test ROI with different energy prices."""
    energy_kwh = 18000
    area = 100
    cost_per_m2 = 200
    
    prices = [0.15, 0.25, 0.35]  # Different energy prices
    
    for price in prices:
        roi = calculate_roi(energy_kwh, price, cost_per_m2, area)
        # Higher price should give better ROI
        assert isinstance(roi, float)


# =============================================================================
# Payback Period Tests
# =============================================================================

def test_calculate_payback_period():
    """Test payback period calculation."""
    energy_kwh = 18000
    energy_price = 0.25
    cost_per_m2 = 200
    area = 100
    
    payback = calculate_payback_period(energy_kwh, energy_price, cost_per_m2, area)
    
    # Cost = 20000, Annual revenue = 4500
    # Payback = 20000 / 4500 ≈ 4.44 years
    assert payback == pytest.approx(4.44, rel=1e-2)


def test_calculate_payback_period_short():
    """Test payback period with high energy production."""
    energy_kwh = 50000
    energy_price = 0.25
    cost_per_m2 = 200
    area = 100
    
    payback = calculate_payback_period(energy_kwh, energy_price, cost_per_m2, area)
    
    # Cost = 20000, Annual revenue = 12500
    # Payback = 20000 / 12500 = 1.6 years
    assert payback == pytest.approx(1.6, rel=1e-2)


def test_calculate_payback_period_long():
    """Test payback period with low energy production."""
    energy_kwh = 5000
    energy_price = 0.25
    cost_per_m2 = 200
    area = 100
    
    payback = calculate_payback_period(energy_kwh, energy_price, cost_per_m2, area)
    
    # Cost = 20000, Annual revenue = 1250
    # Payback = 20000 / 1250 = 16 years
    assert payback == pytest.approx(16.0, rel=1e-2)


def test_calculate_payback_period_zero_energy():
    """Test payback period with zero energy production."""
    payback = calculate_payback_period(0, 0.25, 200, 100)
    assert payback == float('inf')


def test_calculate_payback_period_zero_area():
    """Test payback period with zero area."""
    payback = calculate_payback_period(18000, 0.25, 200, 0)
    assert payback == float('inf')


def test_calculate_payback_period_various_costs():
    """Test payback period with various installation costs."""
    energy_kwh = 18000
    energy_price = 0.25
    area = 100
    
    costs = [150, 200, 250, 300]  # Different costs per m²
    
    previous_payback = 0
    for cost in costs:
        payback = calculate_payback_period(energy_kwh, energy_price, cost, area)
        # Higher cost should mean longer payback
        assert payback > previous_payback
        previous_payback = payback


def test_calculate_payback_period_realistic():
    """Test payback period with realistic values."""
    energy_kwh = 24000  # Good production
    energy_price = 0.23  # Current Netherlands rate
    cost_per_m2 = 180  # Typical installation cost
    area = 150  # Medium roof
    
    payback = calculate_payback_period(energy_kwh, energy_price, cost_per_m2, area)
    
    # Should be reasonable (4-8 years typical)
    assert 3 <= payback <= 10


# =============================================================================
# Edge Cases and Integration Tests
# =============================================================================

def test_solar_calculations_consistency():
    """Test that solar calculations are consistent with each other."""
    area = 100
    irradiance = 1000
    efficiency = 0.18
    shading = 0.2
    energy_price = 0.25
    cost_per_m2 = 200
    
    # Calculate energy
    energy = calculate_solar_potential(area, irradiance, efficiency, shading)
    
    # Calculate payback
    payback = calculate_payback_period(energy, energy_price, cost_per_m2, area)
    
    # Calculate ROI
    roi = calculate_roi(energy, energy_price, cost_per_m2, area)
    
    # All should be valid numbers
    assert energy > 0
    assert payback > 0
    assert -100 <= roi <= 100  # ROI percentage bounds


def test_solar_potential_proportionality():
    """Test that doubling area doubles energy output."""
    irradiance = 1000
    efficiency = 0.18
    shading = 0.1
    
    energy_100 = calculate_solar_potential(100, irradiance, efficiency, shading)
    energy_200 = calculate_solar_potential(200, irradiance, efficiency, shading)
    
    assert energy_200 == pytest.approx(2 * energy_100, rel=1e-2)
