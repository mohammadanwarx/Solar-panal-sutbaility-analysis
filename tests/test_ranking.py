"""
Unit tests for ranking and suitability scoring.
"""

import pytest
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon
from src.ranking import (
    calculate_suitability_score,
    classify_building_suitability,
    rank_buildings,
    get_priority_list
)


# =============================================================================
# Suitability Score Tests
# =============================================================================

def test_calculate_suitability_score_excellent():
    """Test suitability score for an excellent building."""
    score = calculate_suitability_score(
        roof_area=500,        # Large roof
        energy_potential=50000,  # High energy
        shading_factor=0.0,   # No shading
        orientation=180       # South-facing
    )
    
    # Should get high score
    assert score >= 80


def test_calculate_suitability_score_poor():
    """Test suitability score for a poor building."""
    score = calculate_suitability_score(
        roof_area=20,         # Small roof
        energy_potential=1000,   # Low energy
        shading_factor=0.8,   # Heavy shading
        orientation=0         # North-facing
    )
    
    # Should get low score
    assert score < 40


def test_calculate_suitability_score_medium():
    """Test suitability score for a medium building."""
    score = calculate_suitability_score(
        roof_area=150,
        energy_potential=15000,
        shading_factor=0.2,
        orientation=135
    )
    
    # Should get medium score
    assert 40 <= score <= 80


def test_calculate_suitability_score_custom_weights():
    """Test suitability score with custom weights."""
    custom_weights = {
        'area': 0.3,
        'energy': 0.5,
        'shading': 0.1,
        'orientation': 0.1
    }
    
    score = calculate_suitability_score(
        roof_area=200,
        energy_potential=20000,
        shading_factor=0.1,
        orientation=180,
        weights=custom_weights
    )
    
    # Should return valid score
    assert 0 <= score <= 100


def test_calculate_suitability_score_zero_values():
    """Test suitability score with zero values."""
    score = calculate_suitability_score(
        roof_area=0,
        energy_potential=0,
        shading_factor=0,
        orientation=0
    )
    
    # Should return low score but not error
    assert 0 <= score <= 100


def test_calculate_suitability_score_boundary():
    """Test suitability score at boundary values."""
    score = calculate_suitability_score(
        roof_area=500,
        energy_potential=100000,
        shading_factor=1.0,  # Maximum shading
        orientation=180
    )
    
    # Even with maximum shading (weight=0.2), other factors (area, energy, orientation)
    # contribute 80% of score, so score can still be relatively high
    assert 0 <= score <= 100
    # Shading factor contributes 0 points, but other factors still contribute
    assert score >= 60  # From area (20%), energy (40%), and orientation (20%)


# =============================================================================
# Classification Tests
# =============================================================================

def test_classify_building_suitability_excellent():
    """Test classification of excellent buildings."""
    category = classify_building_suitability(85)
    assert category == "Excellent"


def test_classify_building_suitability_good():
    """Test classification of good buildings."""
    category = classify_building_suitability(65)
    assert category == "Good"


def test_classify_building_suitability_moderate():
    """Test classification of moderate buildings."""
    category = classify_building_suitability(50)
    assert category == "Moderate"


def test_classify_building_suitability_poor():
    """Test classification of poor buildings."""
    category = classify_building_suitability(25)
    assert category == "Poor"


def test_classify_building_suitability_unsuitable():
    """Test classification of unsuitable buildings."""
    category = classify_building_suitability(10)
    assert category == "Unsuitable"


def test_classify_building_suitability_boundaries():
    """Test classification at boundary values."""
    assert classify_building_suitability(80) == "Excellent"
    assert classify_building_suitability(79.9) == "Good"
    assert classify_building_suitability(60) == "Good"
    assert classify_building_suitability(59.9) == "Moderate"


# =============================================================================
# Ranking Tests
# =============================================================================

def test_rank_buildings():
    """Test building ranking functionality."""
    # Create sample GeoDataFrame
    data = {
        'building_id': [1, 2, 3, 4, 5],
        'suitability_score': [85, 45, 92, 30, 67],
        'geometry': [Point(0, 0), Point(1, 1), Point(2, 2), Point(3, 3), Point(4, 4)]
    }
    gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")
    
    ranked = rank_buildings(gdf)
    
    # Check that buildings are ranked correctly
    assert ranked.iloc[0]['building_id'] == 3  # Score 92
    assert ranked.iloc[1]['building_id'] == 1  # Score 85
    assert ranked.iloc[2]['building_id'] == 5  # Score 67
    assert ranked.iloc[3]['building_id'] == 2  # Score 45
    assert ranked.iloc[4]['building_id'] == 4  # Score 30
    
    # Check rank column
    assert list(ranked['rank']) == [1, 2, 3, 4, 5]


def test_rank_buildings_with_ties():
    """Test ranking with tied suitability scores."""
    data = {
        'building_id': [1, 2, 3, 4],
        'suitability_score': [80, 80, 90, 70],
        'geometry': [Point(i, i) for i in range(4)]
    }
    gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")
    
    ranked = rank_buildings(gdf)
    
    # Top should be building 3
    assert ranked.iloc[0]['building_id'] == 3
    # Bottom should be building 4
    assert ranked.iloc[3]['building_id'] == 4


def test_rank_buildings_empty():
    """Test ranking with empty GeoDataFrame."""
    gdf = gpd.GeoDataFrame(columns=['suitability_score', 'geometry'])
    ranked = rank_buildings(gdf)
    
    assert len(ranked) == 0
    assert 'rank' in ranked.columns


def test_rank_buildings_single():
    """Test ranking with single building."""
    data = {
        'building_id': [1],
        'suitability_score': [75],
        'geometry': [Point(0, 0)]
    }
    gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")
    
    ranked = rank_buildings(gdf)
    
    assert len(ranked) == 1
    assert ranked.iloc[0]['rank'] == 1


# =============================================================================
# Priority List Tests
# =============================================================================

def test_get_priority_list():
    """Test getting top priority buildings."""
    data = {
        'building_id': range(1, 21),
        'suitability_score': np.random.randint(40, 95, 20),
        'geometry': [Point(i, i) for i in range(20)]
    }
    gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")
    
    top_10 = get_priority_list(gdf, top_n=10)
    
    assert len(top_10) == 10
    # Check that scores are descending
    scores = top_10['suitability_score'].values
    assert all(scores[i] >= scores[i+1] for i in range(len(scores)-1))


def test_get_priority_list_more_than_available():
    """Test getting more buildings than available."""
    data = {
        'building_id': [1, 2, 3],
        'suitability_score': [80, 70, 60],
        'geometry': [Point(i, i) for i in range(3)]
    }
    gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")
    
    top_10 = get_priority_list(gdf, top_n=10)
    
    # Should return all available buildings
    assert len(top_10) == 3


def test_get_priority_list_ranking_preserved():
    """Test that priority list preserves correct ranking."""
    data = {
        'building_id': range(1, 101),
        'suitability_score': range(100, 0, -1),  # Decreasing scores
        'geometry': [Point(i, i) for i in range(100)]
    }
    gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")
    
    top_20 = get_priority_list(gdf, top_n=20)
    
    # Top 20 should have scores 100 down to 81
    expected_scores = list(range(100, 80, -1))
    actual_scores = top_20['suitability_score'].values
    assert list(actual_scores) == expected_scores
