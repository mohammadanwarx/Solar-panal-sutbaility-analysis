"""
Solar Energy Module
Calculates solar energy potential for buildings.
"""
# Tuesday

import numpy as np
from typing import Optional


def calculate_solar_potential(
    area: float,
    irradiance: float,
    efficiency: float = 0.18,
    shading_factor: float = 0.0
) -> float:
    """
    Calculate annual solar energy production potential.
    
    Mathematical formula:
    E = A × H × η × (1 - S)
    
    Parameters
    ----------
    area : float
        Roof area in m²
    irradiance : float
        Annual solar irradiance in kWh/m²/year
    efficiency : float
        Panel efficiency (default 18% = 0.18)
    shading_factor : float
        Shading factor between 0 (no shade) and 1 (full shade)
    
    Returns
    -------
    float
        Annual energy production in kWh
    """
    if area <= 0 or irradiance <= 0:
        return 0.0
    
    if not 0 <= shading_factor <= 1:
        raise ValueError("Shading factor must be between 0 and 1")
    
    energy = area * irradiance * efficiency * (1 - shading_factor)
    return energy


def calculate_roi(
    energy_kwh: float,
    energy_price: float = 0.25,
    installation_cost_per_m2: float = 200,
    area: float = 0
) -> float:
    """
    Calculate Return on Investment (ROI).
    
    Mathematical formula:
    ROI = (E × Price - Cost) / Cost
    
    Parameters
    ----------
    energy_kwh : float
        Annual energy production in kWh
    energy_price : float
        Energy price per kWh (default €0.25)
    installation_cost_per_m2 : float
        Installation cost per m² (default €200)
    area : float
        Roof area in m²
    
    Returns
    -------
    float
        ROI as a percentage
    """
    if area <= 0:
        return 0.0
    
    cost = area * installation_cost_per_m2
    annual_revenue = energy_kwh * energy_price
    
    if cost == 0:
        return 0.0
    
    roi = (annual_revenue - cost) / cost
    return roi * 100  # Convert to percentage


def calculate_payback_period(
    energy_kwh: float,
    energy_price: float = 0.25,
    installation_cost_per_m2: float = 200,
    area: float = 0
) -> float:
    """
    Calculate payback period in years.
    
    Parameters
    ----------
    energy_kwh : float
        Annual energy production in kWh
    energy_price : float
        Energy price per kWh
    installation_cost_per_m2 : float
        Installation cost per m²
    area : float
        Roof area in m²
    
    Returns
    -------
    float
        Payback period in years
    """
    if area <= 0 or energy_kwh <= 0:
        return float('inf')
    
    cost = area * installation_cost_per_m2
    annual_revenue = energy_kwh * energy_price
    
    if annual_revenue == 0:
        return float('inf')
    
    return cost / annual_revenue


# ============================================================================
# Main execution
# ============================================================================

if __name__ == "__main__":
    import geopandas as gpd
    import pandas as pd
    
    # =============================================================================
    # FULL AMSTERDAM DATA (Run once to calculate complete dataset)
    # Uncomment the block below to process full Amsterdam data
    # =============================================================================
    """
    print("=" * 70)
    print("SOLAR ENERGY CALCULATIONS - FULL AMSTERDAM DATA")
    print("=" * 70)
    
    # Load processed buildings with solar data
    buildings_gdf = gpd.read_file("data/processed_buildings.json")
    
    print(f"Calculating solar potential for {len(buildings_gdf)} buildings...")
    
    # Calculate solar potential
    # Note: solar_irradiance is E_y from PVGIS (kWh/m²/year equivalent)
    buildings_gdf['solar_potential_kwh'] = buildings_gdf.apply(
        lambda row: calculate_solar_potential(
            area=row.get('roof_area_m2', 0),
            irradiance=row.get('solar_irradiance', 0) if row.get('solar_irradiance', 0) > 0 else 1000,
            efficiency=0.18,
            shading_factor=row.get('shading_factor', 0)
        ), axis=1
    )
    
    # Calculate ROI metrics
    buildings_gdf['annual_savings_eur'] = buildings_gdf.apply(
        lambda row: calculate_roi(
            energy_kwh=row.get('solar_potential_kwh', 0),
            energy_price=0.25
        ), axis=1
    )
    
    buildings_gdf['payback_period_years'] = buildings_gdf.apply(
        lambda row: calculate_payback_period(
            energy_kwh=row.get('solar_potential_kwh', 0),
            energy_price=0.25,
            installation_cost_per_m2=200,
            area=row.get('roof_area_m2', 0)
        ), axis=1
    )
    
    # Save results
    buildings_gdf.to_file("data/buildings_with_solar_analysis.json", driver="GeoJSON")
    print(f"✓ Solar analysis complete! Saved to data/buildings_with_solar_analysis.json")
    
    print(f"\nSolar Energy Statistics:")
    print(f"  Total potential: {buildings_gdf['solar_potential_kwh'].sum():,.0f} kWh/year")
    print(f"  Average per building: {buildings_gdf['solar_potential_kwh'].mean():,.0f} kWh/year")
    print(f"  Average payback: {buildings_gdf['payback_period_years'].median():.1f} years")
    """
    
    # =============================================================================
    # TEST DATA (Smaller subset for development and testing)
    # This runs by default for quick iterations
    # =============================================================================
    print("=" * 70)
    print("SOLAR ENERGY CALCULATIONS - TEST DATA (Small area for quick testing)")
    print("=" * 70)
    
    # Load processed test buildings
    buildings_gdf = gpd.read_file("data/processed_test_buildings.json")
    
    print(f"Calculating solar potential for {len(buildings_gdf)} buildings...")
    
    # Calculate solar potential
    # Note: solar_irradiance is E_y from PVGIS (kWh/m²/year equivalent)
    buildings_gdf['solar_potential_kwh'] = buildings_gdf.apply(
        lambda row: calculate_solar_potential(
            area=row.get('roof_area_m2', 0),
            irradiance=row.get('solar_irradiance', 0) if row.get('solar_irradiance', 0) > 0 else 1000,
            efficiency=0.18,
            shading_factor=row.get('shading_factor', 0.1)  # Assume small default shading
        ), axis=1
    )
    
    # Calculate ROI metrics
    buildings_gdf['annual_savings_eur'] = buildings_gdf.apply(
        lambda row: calculate_roi(
            energy_kwh=row.get('solar_potential_kwh', 0),
            energy_price=0.25
        ), axis=1
    )
    
    buildings_gdf['payback_period_years'] = buildings_gdf.apply(
        lambda row: calculate_payback_period(
            energy_kwh=row.get('solar_potential_kwh', 0),
            energy_price=0.25,
            installation_cost_per_m2=200,
            area=row.get('roof_area_m2', 0)
        ), axis=1
    )
    
    # Save results
    buildings_gdf.to_file("data/test_buildings_with_solar_analysis.json", driver="GeoJSON")
    print(f"✓ Solar analysis complete! Saved to data/test_buildings_with_solar_analysis.json")
    
    print(f"\nSolar Energy Statistics:")
    print(f"  Total potential: {buildings_gdf['solar_potential_kwh'].sum():,.0f} kWh/year")
    print(f"  Average per building: {buildings_gdf['solar_potential_kwh'].mean():,.0f} kWh/year")
    print(f"  Average payback: {buildings_gdf['payback_period_years'].median():.1f} years")
    
    print("\n✓ Test data solar analysis complete!")
