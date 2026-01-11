"""
Unit tests for spatial search algorithms.
"""

import pytest
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, Polygon
from src.spatial_search import (
    SpatialIndex,
    binary_search_building_by_score,
    quicksort_buildings,
    linear_search_building_by_id,
    find_top_k_buildings
)


@pytest.fixture
def sample_buildings_gdf():
    """Create sample buildings GeoDataFrame for testing."""
    data = {
        'building_id': ['A', 'B', 'C', 'D', 'E'],
        'suitability_score': [45, 92, 30, 67, 85],
        'geometry': [
            Point(0, 0).buffer(10),
            Point(50, 50).buffer(10),
            Point(100, 0).buffer(10),
            Point(0, 100).buffer(10),
            Point(50, 0).buffer(10)
        ]
    }
    return gpd.GeoDataFrame(data, crs="EPSG:28992")  # Dutch projected CRS


def test_spatial_index_creation(sample_buildings_gdf):
    """Test KD-tree spatial index construction."""
    spatial_index = SpatialIndex(sample_buildings_gdf)
    
    assert spatial_index.kdtree is not None
    assert len(spatial_index.coordinates) == 5
    assert spatial_index.buildings_gdf['x'].notna().all()
    assert spatial_index.buildings_gdf['y'].notna().all()


def test_find_nearest_neighbors(sample_buildings_gdf):
    """Test KD-tree nearest neighbor search."""
    spatial_index = SpatialIndex(sample_buildings_gdf)
    query_point = Point(0, 0)
    
    # Find 3 nearest neighbors
    nearest = spatial_index.find_nearest_neighbors(query_point, k=3)
    
    assert len(nearest) == 3
    assert 'distance' in nearest.columns
    # Nearest should be building at (0,0)
    assert nearest.iloc[0]['distance'] < 1


def test_find_within_radius(sample_buildings_gdf):
    """Test KD-tree range search."""
    spatial_index = SpatialIndex(sample_buildings_gdf)
    query_point = Point(0, 0)
    radius = 60  # Should find buildings within 60 units
    
    nearby = spatial_index.find_within_radius(query_point, radius)
    
    assert len(nearby) > 0
    assert all(nearby['distance'] <= radius)
    # Results should be sorted by distance
    assert nearby['distance'].is_monotonic_increasing


def test_binary_search_building_by_score(sample_buildings_gdf):
    """Test binary search for building by score."""
    # Sort by score for binary search
    sorted_gdf = sample_buildings_gdf.sort_values('suitability_score')
    
    # Search for score closest to 70
    idx = binary_search_building_by_score(sorted_gdf, target_score=70)
    
    assert idx is not None
    found_score = sorted_gdf.iloc[idx]['suitability_score']
    # Should find building with score 67 (closest to 70)
    assert found_score == 67


def test_binary_search_exact_match(sample_buildings_gdf):
    """Test binary search with exact score match."""
    sorted_gdf = sample_buildings_gdf.sort_values('suitability_score')
    
    # Search for exact score
    idx = binary_search_building_by_score(sorted_gdf, target_score=85)
    
    assert idx is not None
    assert sorted_gdf.iloc[idx]['suitability_score'] == 85


def test_quicksort_buildings_descending(sample_buildings_gdf):
    """Test quicksort algorithm (descending order)."""
    sorted_gdf = quicksort_buildings(sample_buildings_gdf, ascending=False)
    
    # Check correct order: 92, 85, 67, 45, 30
    expected_order = [92, 85, 67, 45, 30]
    actual_order = sorted_gdf['suitability_score'].tolist()
    
    assert actual_order == expected_order


def test_quicksort_buildings_ascending(sample_buildings_gdf):
    """Test quicksort algorithm (ascending order)."""
    sorted_gdf = quicksort_buildings(sample_buildings_gdf, ascending=True)
    
    # Check correct order: 30, 45, 67, 85, 92
    expected_order = [30, 45, 67, 85, 92]
    actual_order = sorted_gdf['suitability_score'].tolist()
    
    assert actual_order == expected_order


def test_linear_search_building_by_id(sample_buildings_gdf):
    """Test linear search for building by ID."""
    result = linear_search_building_by_id(sample_buildings_gdf, 'C')
    
    assert result is not None
    assert len(result) == 1
    assert result.iloc[0]['building_id'] == 'C'


def test_linear_search_not_found(sample_buildings_gdf):
    """Test linear search with non-existent ID."""
    result = linear_search_building_by_id(sample_buildings_gdf, 'Z')
    assert result is None


def test_find_top_k_buildings(sample_buildings_gdf):
    """Test finding top k buildings."""
    top_3 = find_top_k_buildings(sample_buildings_gdf, k=3)
    
    assert len(top_3) == 3
    # Should get buildings with scores: 92, 85, 67
    scores = sorted(top_3['suitability_score'].tolist(), reverse=True)
    assert scores == [92, 85, 67]


def test_find_top_k_more_than_available(sample_buildings_gdf):
    """Test top k when k > number of buildings."""
    top_10 = find_top_k_buildings(sample_buildings_gdf, k=10)
    
    # Should return all 5 buildings
    assert len(top_10) == 5
