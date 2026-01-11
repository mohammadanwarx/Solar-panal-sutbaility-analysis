"""
Ranking Module
Calculates suitability scores and ranks buildings for solar panel installation.
"""
# Wednesday

import numpy as np
import pandas as pd
import geopandas as gpd
from typing import Dict, List


def calculate_suitability_score(
    roof_area: float,
    energy_potential: float,
    shading_factor: float,
    orientation: float,
    weights: Dict[str, float] = None
) -> float:
    """
    Calculate overall suitability score using weighted combination.
    
    Parameters
    ----------
    roof_area : float
        Roof area in m²
    energy_potential : float
        Annual energy potential in kWh
    shading_factor : float
        Shading factor (0-1, lower is better)
    orientation : float
        Roof orientation in degrees (0-360)
    weights : dict, optional
        Weights for each factor
    
    Returns
    -------
    float
        Suitability score (0-100)
    """
    if weights is None:
        weights = {
            'area': 0.2,
            'energy': 0.4,
            'shading': 0.2,
            'orientation': 0.2
        }
    
    # Normalize factors to 0-1 scale
    area_score = min(roof_area / 500, 1.0)  # Assume 500m² is ideal
    energy_score = min(energy_potential / 50000, 1.0)  # Normalize energy
    shading_score = 1 - shading_factor  # Lower shading is better
    
    # Orientation score: South-facing (180°) is optimal
    orientation_diff = abs(orientation - 180)
    orientation_score = 1 - (orientation_diff / 180)
    
    # Weighted combination
    total_score = (
        area_score * weights['area'] +
        energy_score * weights['energy'] +
        shading_score * weights['shading'] +
        orientation_score * weights['orientation']
    )
    
    return total_score * 100  # Convert to 0-100 scale


def classify_building_suitability(score: float) -> str:
    """
    Classify building into suitability categories.
    
    Parameters
    ----------
    score : float
        Suitability score (0-100)
    
    Returns
    -------
    str
        Suitability category
    """
    if score >= 80:
        return "Excellent"
    elif score >= 60:
        return "Good"
    elif score >= 40:
        return "Moderate"
    elif score >= 20:
        return "Poor"
    else:
        return "Unsuitable"


def rank_buildings(buildings_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Rank buildings by suitability score.
    
    Parameters
    ----------
    buildings_gdf : gpd.GeoDataFrame
        GeoDataFrame with suitability scores
    
    Returns
    -------
    gpd.GeoDataFrame
        Ranked buildings with priority order
    """
    # Sort by suitability score (descending)
    ranked = buildings_gdf.sort_values('suitability_score', ascending=False)
    ranked['rank'] = range(1, len(ranked) + 1)
    
    return ranked


def get_priority_list(
    buildings_gdf: gpd.GeoDataFrame,
    top_n: int = 100
) -> gpd.GeoDataFrame:
    """
    Get top N priority buildings for installation.
    
    Parameters
    ----------
    buildings_gdf : gpd.GeoDataFrame
        GeoDataFrame with suitability scores
    top_n : int
        Number of top buildings to return
    
    Returns
    -------
    gpd.GeoDataFrame
        Top priority buildings
    """
    ranked = rank_buildings(buildings_gdf)
    return ranked.head(top_n)


# ============================================================================
# Main execution
# ============================================================================

if __name__ == "__main__":
    # =============================================================================
    # FULL AMSTERDAM DATA (Run once to rank complete dataset)
    # Uncomment the block below to process full Amsterdam data
    # =============================================================================
    """
    print("=" * 70)
    print("RANKING FULL AMSTERDAM DATA")
    print("=" * 70)
    
    # Load processed buildings
    buildings_gdf = gpd.read_file("data/processed_buildings.json")
    
    # Calculate suitability scores
    print("Calculating suitability scores...")
    buildings_gdf['suitability_score'] = buildings_gdf.apply(
        lambda row: calculate_suitability_score(
            roof_area=row.get('roof_area_m2', 0),
            energy_potential=row.get('solar_energy_kwh', 0),
            shading_factor=row.get('shading_factor', 0),
            orientation=row.get('roof_orientation_deg', 0)
        ), axis=1
    )
    
    # Rank buildings
    print("Ranking buildings...")
    ranked_buildings = rank_buildings(buildings_gdf)
    
    # Save ranked results
    ranked_buildings.to_file("data/ranked_buildings.json", driver="GeoJSON")
    print(f"✓ Ranked {len(ranked_buildings)} buildings saved to data/ranked_buildings.json")
    
    # Get top priority buildings
    top_buildings = get_priority_list(ranked_buildings, top_n=100)
    top_buildings.to_file("data/top_100_buildings.json", driver="GeoJSON")
    print(f"✓ Top 100 buildings saved to data/top_100_buildings.json")
    
    print(f"\nTop 5 Buildings:")
    for idx, row in top_buildings.head(5).iterrows():
        print(f"  Rank {row['rank']}: Score {row['suitability_score']:.2f}")
    """
    
    # =============================================================================
    # TEST DATA (Smaller subset for development and testing)
    # This runs by default for quick iterations
    # =============================================================================
    print("=" * 70)
    print("RANKING TEST DATA (Small area for quick testing)")
    print("=" * 70)
    
    # Load processed test buildings
    buildings_gdf = gpd.read_file("data/processed_test_buildings.json")
    
    # Calculate suitability scores
    print("Calculating suitability scores...")
    buildings_gdf['suitability_score'] = buildings_gdf.apply(
        lambda row: calculate_suitability_score(
            roof_area=row.get('roof_area_m2', 0),
            energy_potential=row.get('solar_energy_kwh', 0),
            shading_factor=row.get('shading_factor', 0),
            orientation=row.get('roof_orientation_deg', 0)
        ), axis=1
    )
    
    # Rank buildings
    print("Ranking buildings...")
    ranked_buildings = rank_buildings(buildings_gdf)
    
    # Save ranked results
    ranked_buildings.to_file("data/ranked_test_buildings.json", driver="GeoJSON")
    print(f"✓ Ranked {len(ranked_buildings)} buildings saved to data/ranked_test_buildings.json")
    
    # Get top priority buildings
    top_buildings = get_priority_list(ranked_buildings, top_n=20)
    top_buildings.to_file("data/top_20_test_buildings.json", driver="GeoJSON")
    print(f"✓ Top 20 buildings saved to data/top_20_test_buildings.json")
    
    print(f"\nTop 5 Buildings:")
    for idx, row in top_buildings.head(5).iterrows():
        print(f"  Rank {row['rank']}: Score {row['suitability_score']:.2f}")
    
    print("\n✓ Test data ranking complete!")
