"""
Shading Analysis Module
Calculates shading effects from nearby buildings.
"""
# Monday

import numpy as np
import geopandas as gpd
from shapely.geometry import Point, Polygon
from typing import List, Tuple

try:
    from src.spatial_search import SpatialIndex
except ModuleNotFoundError:
    from spatial_search import SpatialIndex


def calculate_shading_factor(
    building_geometry: Polygon,
    building_height: float,
    nearby_buildings: gpd.GeoDataFrame,
    sun_elevation: float = 45.0
) -> float:
    """
    Calculate shading factor for a building based on nearby obstructions.
    
    Parameters
    ----------
    building_geometry : Polygon
        Target building geometry
    building_height : float
        Target building height in meters
    nearby_buildings : gpd.GeoDataFrame
        GeoDataFrame of nearby buildings with heights
    sun_elevation : float
        Average sun elevation angle in degrees (default 45°)
    
    Returns
    -------
    float
        Shading factor between 0 (no shade) and 1 (full shade)
    """
    if len(nearby_buildings) == 0:
        return 0.0  # No nearby buildings, no shading
    
    # Get target building centroid
    target_centroid = building_geometry.centroid
    
    shading_scores = []
    
    for idx, nearby in nearby_buildings.iterrows():
        # Get nearby building properties
        nearby_geom = nearby.geometry
        nearby_height = nearby.get('building_height', nearby.get('height', 10.0))
        
        # Calculate distance between centroids
        distance = target_centroid.distance(nearby_geom.centroid)
        
        if distance < 1:  # Skip if same building (distance ~0)
            continue
        
        # Calculate height difference
        height_diff = nearby_height - building_height
        
        # Only consider taller buildings that can cast shadows
        if height_diff > 0:
            # Calculate shadow length from nearby building
            shadow_length = calculate_shadow_length(nearby_height, sun_elevation)
            
            # If target building is within shadow range
            if distance <= shadow_length:
                # Shading intensity decreases with distance
                # Formula: intensity = height_diff * (1 - distance/shadow_length)
                intensity = (height_diff / 50.0) * (1 - distance / shadow_length)
                intensity = min(intensity, 1.0)  # Cap at 1.0
                
                # Consider building size (larger buildings cast more shadow)
                size_factor = min(nearby_geom.area / building_geometry.area, 2.0)
                intensity *= (0.5 + 0.5 * min(size_factor, 1.0))
                
                shading_scores.append(intensity)
    
    if not shading_scores:
        return 0.0
    
    # Aggregate shading from multiple buildings
    # Use root mean square to avoid overestimating combined shading
    total_shading = np.sqrt(np.mean(np.array(shading_scores) ** 2))
    
    # Normalize to 0-1 range
    return min(total_shading, 1.0)


def find_nearby_buildings(
    target_building: Polygon,
    all_buildings: gpd.GeoDataFrame,
    search_radius: float = 100.0
) -> gpd.GeoDataFrame:
    """
    Find buildings within a given radius using spatial search (KD-tree).
    
    Uses KD-tree spatial index for efficient range queries.
    Time Complexity: O(log n + m) where m is number of results
    
    Parameters
    ----------
    target_building : Polygon
        Target building geometry
    all_buildings : gpd.GeoDataFrame
        All buildings in the area
    search_radius : float
        Search radius in meters (default 100m)
    
    Returns
    -------
    gpd.GeoDataFrame
        Nearby buildings within radius, sorted by distance
    """
    # Build spatial index using KD-tree
    spatial_index = SpatialIndex(all_buildings)
    
    # Get centroid of target building
    target_centroid = target_building.centroid
    
    # Use KD-tree range query to find buildings within radius
    nearby_buildings = spatial_index.find_within_radius(target_centroid, radius=search_radius)
    
    # If no nearby buildings found, return empty dataframe
    if len(nearby_buildings) == 0:
        return nearby_buildings
    
    # Calculate distances and sort
    nearby_buildings['distance'] = nearby_buildings.geometry.apply(
        lambda geom: target_centroid.distance(geom.centroid)
    )
    
    # Remove self (distance < 1m) and sort by distance
    nearby_buildings = nearby_buildings[nearby_buildings['distance'] >= 1.0]
    nearby_buildings = nearby_buildings.sort_values('distance')
    
    return nearby_buildings
    
    return nearby


def calculate_shadow_length(
    building_height: float,
    sun_elevation: float
) -> float:
    """
    Calculate shadow length from a building.
    
    Parameters
    ----------
    building_height : float
        Building height in meters
    sun_elevation : float
        Sun elevation angle in degrees
    
    Returns
    -------
    float
        Shadow length in meters
    """
    if sun_elevation <= 0 or sun_elevation >= 90:
        return 0.0
    
    sun_elevation_rad = np.radians(sun_elevation)
    shadow_length = building_height / np.tan(sun_elevation_rad)
    
    return shadow_length


# ============================================================================
# Main execution
# ============================================================================

if __name__ == "__main__":
    # =============================================================================
    # FULL AMSTERDAM DATA (Run once to analyze complete dataset)
    # Uncomment the block below to process full Amsterdam data
    # =============================================================================
    """
    print("=" * 70)
    print("SHADING ANALYSIS - FULL AMSTERDAM DATA")
    print("=" * 70)
    
    # Load processed buildings
    buildings_gdf = gpd.read_file("data/processed_buildings.json")
    
    print(f"Analyzing shading for {len(buildings_gdf)} buildings...")
    
    # Build spatial index for efficient neighbor search
    spatial_idx = SpatialIndex(buildings_gdf)
    
    # Calculate shading factors
    shading_factors = []
    for idx, building in buildings_gdf.iterrows():
        nearby = spatial_idx.find_within_radius(
            building.geometry.centroid,
            radius=100.0
        )
        
        if len(nearby) > 1:  # Exclude self
            shading = calculate_shading_factor(
                building.geometry,
                building.get('building_height', 10.0),
                nearby,
                sun_elevation=45.0
            )
        else:
            shading = 0.0  # No nearby buildings
        
        shading_factors.append(shading)
    
    buildings_gdf['shading_factor'] = shading_factors
    
    # Save results
    buildings_gdf.to_file("data/buildings_with_shading.json", driver="GeoJSON")
    print(f"✓ Shading analysis complete! Saved to data/buildings_with_shading.json")
    
    print(f"\nShading Statistics:")
    print(f"  Mean shading factor: {np.mean(shading_factors):.3f}")
    print(f"  Buildings with shading > 0.5: {sum(s > 0.5 for s in shading_factors)}")
    """
    
    # =============================================================================
    # TEST DATA (Smaller subset for development and testing)
    # This runs by default for quick iterations
    # =============================================================================
    print("=" * 70)
    print("SHADING ANALYSIS - TEST DATA (Small area for quick testing)")
    print("=" * 70)
    
    # Load processed test buildings
    buildings_gdf = gpd.read_file("data/processed_test_buildings.json")
    
    print(f"Analyzing shading for {len(buildings_gdf)} buildings...")
    
    # Build spatial index for efficient neighbor search
    spatial_idx = SpatialIndex(buildings_gdf)
    
    # Calculate shading factors
    shading_factors = []
    for idx, building in buildings_gdf.iterrows():
        nearby = spatial_idx.find_within_radius(
            building.geometry.centroid,
            radius=100.0
        )
        
        if len(nearby) > 1:  # Exclude self
            # Use full shading calculation
            shading = calculate_shading_factor(
                building.geometry,
                building.get('building_height', 10.0),
                nearby,
                sun_elevation=45.0
            )
        else:
            shading = 0.0  # No nearby buildings
        
        shading_factors.append(shading)
    
    buildings_gdf['shading_factor'] = shading_factors
    
    # Save results
    buildings_gdf.to_file("data/test_buildings_with_shading.json", driver="GeoJSON")
    print(f"✓ Shading analysis complete! Saved to data/test_buildings_with_shading.json")
    
    print(f"\nShading Statistics:")
    print(f"  Mean shading factor: {np.mean(shading_factors):.3f}")
    print(f"  Buildings with shading > 0.3: {sum(s > 0.3 for s in shading_factors)}")
    
    print("\n✓ Test data shading analysis complete!")
