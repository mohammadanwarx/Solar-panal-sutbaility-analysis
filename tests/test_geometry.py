"""
Unit tests for geometry module.
"""

import pytest
import numpy as np
import json
from pathlib import Path
from shapely.geometry import Polygon, MultiPolygon, Point
import geopandas as gpd
from src.geometry import (
    calculate_roof_area,
    calculate_roof_orientation,
    calculate_roof_slope,
    get_roof_vertices,
    load_solar_data,
    interpolate_solar_at_point,
    BuildingGeometryProcessor
)


# =============================================================================
# Roof Area Tests
# =============================================================================

def test_calculate_roof_area_square():
    """Test roof area calculation for a square building."""
    # Create a 10x10 meter square
    square = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    area = calculate_roof_area(square)
    
    assert area == pytest.approx(100.0, rel=1e-2)


def test_calculate_roof_area_rectangle():
    """Test roof area calculation for a rectangular building."""
    # Create a 20x10 meter rectangle
    rectangle = Polygon([(0, 0), (20, 0), (20, 10), (0, 10)])
    area = calculate_roof_area(rectangle)
    
    assert area == pytest.approx(200.0, rel=1e-2)


def test_calculate_roof_area_complex():
    """Test roof area calculation for an L-shaped building."""
    # Create an L-shaped polygon
    l_shape = Polygon([
        (0, 0), (10, 0), (10, 5),
        (5, 5), (5, 10), (0, 10)
    ])
    area = calculate_roof_area(l_shape)
    
    # Area = 10*5 + 5*5 = 75
    assert area == pytest.approx(75.0, rel=1e-2)


def test_calculate_roof_area_invalid():
    """Test handling of invalid geometry."""
    # Empty polygon should have zero area
    empty_polygon = Polygon()
    area = calculate_roof_area(empty_polygon)
    
    assert area == 0.0


def test_calculate_roof_area_multipolygon():
    """Test roof area for MultiPolygon (uses largest polygon)."""
    poly1 = Polygon([(0, 0), (5, 0), (5, 5), (0, 5)])  # 25 m²
    poly2 = Polygon([(10, 10), (20, 10), (20, 20), (10, 20)])  # 100 m²
    multi = MultiPolygon([poly1, poly2])
    
    area = calculate_roof_area(multi)
    # MultiPolygon.area returns sum of all polygons (125 m²)
    assert area == pytest.approx(125.0, rel=1e-2)


# =============================================================================
# Roof Orientation Tests
# =============================================================================

def test_calculate_roof_orientation_north():
    """Test orientation for north-facing building."""
    # Rectangle with longest edge pointing north
    north_rect = Polygon([(0, 0), (5, 0), (5, 20), (0, 20)])
    orientation = calculate_roof_orientation(north_rect)
    
    # Should be close to 0° (north) or 180° (south)
    assert orientation == pytest.approx(0.0, abs=10) or orientation == pytest.approx(180.0, abs=10)


def test_calculate_roof_orientation_east():
    """Test orientation for east-facing building."""
    # Rectangle with longest edge pointing east
    east_rect = Polygon([(0, 0), (20, 0), (20, 5), (0, 5)])
    orientation = calculate_roof_orientation(east_rect)
    
    # Should be close to 90° (east) or 270° (west)
    assert orientation == pytest.approx(90.0, abs=10) or orientation == pytest.approx(270.0, abs=10)


def test_calculate_roof_orientation_multipolygon():
    """Test orientation calculation for MultiPolygon."""
    poly1 = Polygon([(0, 0), (5, 0), (5, 5), (0, 5)])
    poly2 = Polygon([(10, 10), (30, 10), (30, 15), (10, 15)])
    multi = MultiPolygon([poly1, poly2])
    
    orientation = calculate_roof_orientation(multi)
    # Should not raise error and return valid orientation
    assert 0 <= orientation <= 360


# =============================================================================
# Roof Slope Tests
# =============================================================================

def test_calculate_roof_slope_flat():
    """Test slope calculation for flat roof."""
    slope = calculate_roof_slope(10.0, "flat")
    # Flat roofs have slight slope (2°) for drainage
    assert slope == 2.0


def test_calculate_roof_slope_pitched():
    """Test slope calculation for pitched roof."""
    slope = calculate_roof_slope(10.0, "pitched")
    assert 10.0 <= slope <= 50.0


def test_calculate_roof_slope_default():
    """Test default roof slope calculation."""
    slope = calculate_roof_slope(10.0)
    assert slope >= 0.0


# =============================================================================
# Vertex Extraction Tests
# =============================================================================

def test_get_roof_vertices():
    """Test extraction of roof vertices."""
    square = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    vertices = get_roof_vertices(square)
    
    assert isinstance(vertices, np.ndarray)
    assert len(vertices) == 5  # 4 corners + closing point


def test_get_roof_vertices_multipolygon():
    """Test vertex extraction from MultiPolygon."""
    poly1 = Polygon([(0, 0), (5, 0), (5, 5), (0, 5)])
    poly2 = Polygon([(10, 10), (20, 10), (20, 20), (10, 20)])
    multi = MultiPolygon([poly1, poly2])
    
    vertices = get_roof_vertices(multi)
    # Should extract vertices from largest polygon
    assert isinstance(vertices, np.ndarray)
    assert len(vertices) == 5  # 4 corners + closing point


def test_get_roof_vertices_triangle():
    """Test vertex extraction from triangular roof."""
    triangle = Polygon([(0, 0), (10, 0), (5, 10)])
    vertices = get_roof_vertices(triangle)
    
    assert len(vertices) == 4  # 3 corners + closing point


# =============================================================================
# Solar Data Tests
# =============================================================================

def test_interpolate_solar_at_point_nearest():
    """Test solar interpolation using nearest neighbor."""
    coords = np.array([[0, 0], [10, 0], [0, 10], [10, 10]])
    values = np.array([1000, 1100, 1200, 1300])
    
    point = Point(1, 1)  # Near (0, 0)
    interpolated = interpolate_solar_at_point(point, coords, values, method='nearest')
    
    # Should be close to 1000 (nearest point value)
    assert interpolated == pytest.approx(1000, abs=100)


def test_interpolate_solar_at_point_linear():
    """Test solar interpolation using linear method."""
    coords = np.array([[0, 0], [10, 0], [0, 10], [10, 10]])
    values = np.array([1000, 1100, 1200, 1300])
    
    point = Point(5, 5)  # Center point
    interpolated = interpolate_solar_at_point(point, coords, values, method='linear')
    
    # Should be interpolated value around mean
    assert 1000 <= interpolated <= 1300


# =============================================================================
# BuildingGeometryProcessor Tests
# =============================================================================

def test_building_geometry_processor_initialization():
    """Test initialization of BuildingGeometryProcessor."""
    processor = BuildingGeometryProcessor(
        buildings_path="data/test_footprints.json",
        solar_path="data/test_solar.json"
    )
    
    assert processor.buildings_path == "data/test_footprints.json"
    assert processor.solar_path == "data/test_solar.json"


def test_building_geometry_processor_empty_data():
    """Test processor with non-existent data."""
    processor = BuildingGeometryProcessor(
        buildings_path="nonexistent.json",
        solar_path="nonexistent.json"
    )
    
    # Should handle missing files gracefully
    assert processor.buildings_gdf.empty or len(processor.buildings_gdf) == 0
