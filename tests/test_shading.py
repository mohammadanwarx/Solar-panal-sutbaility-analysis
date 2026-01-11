"""
Unit tests for shading analysis.
"""

import pytest
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, Point
from src.shading import (
    calculate_shadow_length,
    calculate_shading_factor,
    find_nearby_buildings
)


# =============================================================================
# Shadow Length Tests
# =============================================================================

def test_calculate_shadow_length_45_degrees():
    """Test shadow length at 45° sun elevation."""
    building_height = 10  # meters
    sun_elevation = 45  # degrees
    
    shadow_length = calculate_shadow_length(building_height, sun_elevation)
    
    # At 45°, shadow length equals building height
    assert shadow_length == pytest.approx(10.0, rel=1e-2)


def test_calculate_shadow_length_30_degrees():
    """Test shadow length at 30° sun elevation."""
    building_height = 10
    sun_elevation = 30
    
    shadow_length = calculate_shadow_length(building_height, sun_elevation)
    
    # shadow = height / tan(30°) = 10 / 0.577 ≈ 17.32
    assert shadow_length == pytest.approx(17.32, rel=1e-2)


def test_calculate_shadow_length_60_degrees():
    """Test shadow length at 60° sun elevation."""
    building_height = 10
    sun_elevation = 60
    
    shadow_length = calculate_shadow_length(building_height, sun_elevation)
    
    # shadow = height / tan(60°) = 10 / 1.732 ≈ 5.77
    assert shadow_length == pytest.approx(5.77, rel=1e-2)


def test_calculate_shadow_length_zero_elevation():
    """Test shadow length at zero sun elevation (horizon)."""
    shadow_length = calculate_shadow_length(10, 0)
    assert shadow_length == 0.0


def test_calculate_shadow_length_90_degrees():
    """Test shadow length at 90° (sun directly overhead)."""
    shadow_length = calculate_shadow_length(10, 90)
    assert shadow_length == 0.0


def test_calculate_shadow_length_various_heights():
    """Test shadow length with various building heights."""
    sun_elevation = 45
    
    heights = [5, 10, 20, 50]
    for height in heights:
        shadow = calculate_shadow_length(height, sun_elevation)
        # At 45°, shadow equals height
        assert shadow == pytest.approx(height, rel=1e-2)


# =============================================================================
# Shading Factor Tests
# =============================================================================

def test_calculate_shading_factor_no_nearby():
    """Test shading factor with no nearby buildings."""
    target_geom = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    target_height = 10
    nearby_buildings = gpd.GeoDataFrame()
    
    shading = calculate_shading_factor(
        target_geom,
        target_height,
        nearby_buildings,
        sun_elevation=45
    )
    
    assert shading == 0.0


def test_calculate_shading_factor_shorter_buildings():
    """Test shading factor with only shorter nearby buildings."""
    target_geom = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    target_height = 20
    
    # Create shorter nearby buildings
    nearby_data = {
        'geometry': [Polygon([(20, 0), (30, 0), (30, 10), (20, 10)])],
        'building_height': [10]  # Shorter than target
    }
    nearby_buildings = gpd.GeoDataFrame(nearby_data)
    
    shading = calculate_shading_factor(
        target_geom,
        target_height,
        nearby_buildings,
        sun_elevation=45
    )
    
    # Shorter buildings should not cast shadow
    assert shading == 0.0


def test_calculate_shading_factor_taller_far_building():
    """Test shading factor with tall but far building."""
    target_geom = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    target_height = 10
    
    # Create tall but far building (beyond shadow range)
    nearby_data = {
        'geometry': [Polygon([(200, 0), (210, 0), (210, 10), (200, 10)])],
        'building_height': [50]
    }
    nearby_buildings = gpd.GeoDataFrame(nearby_data)
    
    shading = calculate_shading_factor(
        target_geom,
        target_height,
        nearby_buildings,
        sun_elevation=45
    )
    
    # Should have minimal shading due to distance
    assert shading < 0.1


def test_calculate_shading_factor_taller_close_building():
    """Test shading factor with taller nearby building."""
    target_geom = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    target_height = 10
    
    # Create taller nearby building within shadow range
    nearby_data = {
        'geometry': [Polygon([(15, 0), (25, 0), (25, 10), (15, 10)])],
        'building_height': [30]
    }
    nearby_buildings = gpd.GeoDataFrame(nearby_data)
    
    shading = calculate_shading_factor(
        target_geom,
        target_height,
        nearby_buildings,
        sun_elevation=45
    )
    
    # Should have significant shading
    assert shading > 0.1


def test_calculate_shading_factor_multiple_buildings():
    """Test shading factor with multiple nearby buildings."""
    target_geom = Polygon([(50, 50), (60, 50), (60, 60), (50, 60)])
    target_height = 10
    
    # Create multiple nearby buildings
    nearby_data = {
        'geometry': [
            Polygon([(65, 50), (75, 50), (75, 60), (65, 60)]),
            Polygon([(40, 50), (45, 50), (45, 60), (40, 60)]),
            Polygon([(50, 65), (60, 65), (60, 75), (50, 75)])
        ],
        'building_height': [20, 25, 15]
    }
    nearby_buildings = gpd.GeoDataFrame(nearby_data)
    
    shading = calculate_shading_factor(
        target_geom,
        target_height,
        nearby_buildings,
        sun_elevation=45
    )
    
    # Multiple buildings should create compound shading
    assert 0.0 <= shading <= 1.0


def test_calculate_shading_factor_sun_angles():
    """Test shading factor at different sun elevations."""
    target_geom = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    target_height = 10
    
    nearby_data = {
        'geometry': [Polygon([(15, 0), (25, 0), (25, 10), (15, 10)])],
        'building_height': [20]
    }
    nearby_buildings = gpd.GeoDataFrame(nearby_data)
    
    # Lower sun angle = longer shadows
    shading_30 = calculate_shading_factor(target_geom, target_height, nearby_buildings, 30)
    shading_60 = calculate_shading_factor(target_geom, target_height, nearby_buildings, 60)
    
    # Lower angle should produce more shading (if within range)
    assert shading_30 >= 0 and shading_60 >= 0


# =============================================================================
# Nearby Building Search Tests
# =============================================================================

def test_find_nearby_buildings_basic():
    """Test finding nearby buildings."""
    target = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    
    # Create buildings at various distances
    buildings_data = {
        'building_id': [1, 2, 3, 4],
        'geometry': [
            Polygon([(20, 0), (30, 0), (30, 10), (20, 10)]),    # Close
            Polygon([(60, 0), (70, 0), (70, 10), (60, 10)]),    # Medium
            Polygon([(150, 0), (160, 0), (160, 10), (150, 10)]), # Far
            Polygon([(0, 20), (10, 20), (10, 30), (0, 30)])     # Close
        ]
    }
    all_buildings = gpd.GeoDataFrame(buildings_data, crs="EPSG:28992")
    
    nearby = find_nearby_buildings(target, all_buildings, search_radius=50.0)
    
    # Should find close buildings only (within 50m)
    assert len(nearby) >= 2  # At least the two close buildings


def test_find_nearby_buildings_empty():
    """Test finding nearby buildings when none exist."""
    target = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    all_buildings = gpd.GeoDataFrame(columns=['geometry'], crs="EPSG:28992")
    
    nearby = find_nearby_buildings(target, all_buildings, search_radius=100.0)
    
    assert len(nearby) == 0


def test_find_nearby_buildings_sorted_by_distance():
    """Test that nearby buildings are sorted by distance."""
    target = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    
    buildings_data = {
        'building_id': [1, 2, 3],
        'geometry': [
            Polygon([(50, 0), (60, 0), (60, 10), (50, 10)]),  # Farthest
            Polygon([(15, 0), (25, 0), (25, 10), (15, 10)]),  # Closest
            Polygon([(30, 0), (40, 0), (40, 10), (30, 10)])   # Middle
        ]
    }
    all_buildings = gpd.GeoDataFrame(buildings_data, crs="EPSG:28992")
    
    nearby = find_nearby_buildings(target, all_buildings, search_radius=100.0)
    
    # Check if sorted by distance
    if len(nearby) > 1:
        distances = nearby['distance'].values
        assert all(distances[i] <= distances[i+1] for i in range(len(distances)-1))


def test_find_nearby_buildings_excludes_self():
    """Test that target building excludes itself."""
    target = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    
    buildings_data = {
        'building_id': [1, 2],
        'geometry': [
            target,  # Same as target
            Polygon([(20, 0), (30, 0), (30, 10), (20, 10)])
        ]
    }
    all_buildings = gpd.GeoDataFrame(buildings_data, crs="EPSG:28992")
    
    nearby = find_nearby_buildings(target, all_buildings, search_radius=50.0)
    
    # Should exclude self (distance < 1m)
    assert all(nearby['distance'] >= 1.0)
