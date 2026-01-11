"""
Unit tests for data acquisition module.
"""

import pytest
import geopandas as gpd
from shapely.geometry import box, Point
import json
from unittest.mock import patch, Mock, MagicMock
from src.data_acquisition import (
    fetch_pdok_buildings,
    PVGISPVCalcClient
)


# ============================================================
# Tests for fetch_pdok_buildings
# ============================================================

def test_fetch_pdok_buildings_with_bbox():
    """Test fetching buildings with a small bounding box."""
    # Small area in Amsterdam (should return quickly)
    bbox = (4.88, 52.36, 4.89, 52.37)
    
    buildings = fetch_pdok_buildings(bbox, output_path=None, page_size=10)
    
    # Assertions
    assert isinstance(buildings, gpd.GeoDataFrame)
    assert buildings.crs.to_string() == "EPSG:28992"
    assert 'geometry' in buildings.columns
    # Should have BAG3D attributes
    if len(buildings) > 0:
        assert 'identificatie' in buildings.columns or 'fid' in buildings.columns


def test_fetch_pdok_buildings_empty_area():
    """Test fetching from an area with no buildings (ocean)."""
    # North Sea coordinates (no buildings expected)
    bbox = (3.0, 52.0, 3.1, 52.1)
    
    buildings = fetch_pdok_buildings(bbox, output_path=None, page_size=10)
    
    assert isinstance(buildings, gpd.GeoDataFrame)
    assert buildings.crs.to_string() == "EPSG:28992"


def test_fetch_pdok_buildings_invalid_input_type():
    """Test that invalid input types raise TypeError."""
    with pytest.raises(TypeError, match="Unsupported area input type"):
        fetch_pdok_buildings(area=[1, 2, 3, 4], output_path=None)


def test_fetch_pdok_buildings_with_geodataframe():
    """Test fetching buildings using GeoDataFrame as input."""
    # Create a small test area as GeoDataFrame
    test_geometry = box(4.88, 52.36, 4.89, 52.37)
    area_gdf = gpd.GeoDataFrame(geometry=[test_geometry], crs="EPSG:4326")
    
    buildings = fetch_pdok_buildings(area=area_gdf, output_path=None, page_size=10)
    
    assert isinstance(buildings, gpd.GeoDataFrame)
    assert buildings.crs.to_string() == "EPSG:28992"


@patch('src.data_acquisition.requests.get')
def test_fetch_pdok_buildings_api_error(mock_get):
    """Test handling of API errors."""
    # Mock a failed HTTP request
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("API Error")
    mock_get.return_value = mock_response
    
    bbox = (4.88, 52.36, 4.89, 52.37)
    
    with pytest.raises(Exception):
        fetch_pdok_buildings(bbox, output_path=None)


# ============================================================
# Tests for PVGISPVCalcClient
# ============================================================

def test_pvgis_client_initialization():
    """Test PVGISPVCalcClient initialization."""
    client = PVGISPVCalcClient(peakpower=2, loss=10, timeout=20)
    
    assert client.peakpower == 2
    assert client.loss == 10
    assert client.timeout == 20


def test_pvgis_client_default_params():
    """Test PVGISPVCalcClient with default parameters."""
    client = PVGISPVCalcClient()
    
    assert client.peakpower == 1
    assert client.loss == 14
    assert client.timeout == 30


@patch('src.data_acquisition.requests.get')
def test_pvgis_fetch_point(mock_get):
    """Test PVGIS single point fetching with mocked response."""
    # Mock successful API response
    mock_response = Mock()
    mock_response.json.return_value = {
        "outputs": {
            "totals": {
                "fixed": {
                    "E_y": 1050.5,
                    "E_m": 87.5,
                    "E_d": 2.88
                }
            }
        }
    }
    mock_get.return_value = mock_response
    
    client = PVGISPVCalcClient()
    result = client._fetch_point(52.36, 4.88)
    
    assert result is not None
    assert 'outputs' in result
    assert result['outputs']['totals']['fixed']['E_y'] == 1050.5


@patch('src.data_acquisition.requests.get')
def test_pvgis_fetch_bbox_geojson(mock_get):
    """Test PVGIS bbox fetching returns valid GeoJSON."""
    # Mock successful API response
    mock_response = Mock()
    mock_response.json.return_value = {
        "outputs": {
            "totals": {
                "fixed": {
                    "E_y": 1000.0
                }
            }
        }
    }
    mock_get.return_value = mock_response
    
    client = PVGISPVCalcClient()
    # Very small bbox to limit API calls in test
    bbox = (4.88, 52.36, 4.881, 52.361)  # ~100m x ~100m
    
    geojson = client.fetch_bbox_geojson(bbox, step_km=0.1, sleep=0)
    
    # Verify GeoJSON structure
    assert geojson['type'] == 'FeatureCollection'
    assert 'features' in geojson
    assert len(geojson['features']) > 0
    
    # Verify feature structure
    feature = geojson['features'][0]
    assert feature['type'] == 'Feature'
    assert feature['geometry']['type'] == 'Point'
    assert 'E_y' in feature['properties']
    assert feature['properties']['source'] == 'PVGIS PVcalc'


@patch('src.data_acquisition.requests.get')
def test_pvgis_api_error_handling(mock_get):
    """Test PVGIS API error handling."""
    # Mock failed HTTP request
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("PVGIS API Error")
    mock_get.return_value = mock_response
    
    client = PVGISPVCalcClient()
    
    with pytest.raises(Exception):
        client._fetch_point(52.36, 4.88)


def test_pvgis_save_geojson(tmp_path):
    """Test saving GeoJSON to file."""
    client = PVGISPVCalcClient()
    
    # Create test GeoJSON
    test_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": 1,
                "geometry": {"type": "Point", "coordinates": [4.88, 52.36]},
                "properties": {"E_y": 1000.0}
            }
        ]
    }
    
    # Save to temporary file
    output_file = tmp_path / "test_solar.json"
    client.save_geojson(test_geojson, str(output_file))
    
    # Verify file was created and contains correct data
    assert output_file.exists()
    
    with open(output_file, 'r') as f:
        loaded = json.load(f)
    
    assert loaded['type'] == 'FeatureCollection'
    assert len(loaded['features']) == 1
    assert loaded['features'][0]['properties']['E_y'] == 1000.0


# ============================================================
# Integration Tests (marked as slow)
# ============================================================

@pytest.mark.slow
def test_fetch_real_pdok_buildings():
    """Integration test: fetch real buildings from PDOK (slow)."""
    # Very small area in Amsterdam city center
    bbox = (4.895, 52.370, 4.896, 52.371)  # ~100m x ~100m
    
    buildings = fetch_pdok_buildings(bbox, output_path=None, page_size=50)
    
    assert isinstance(buildings, gpd.GeoDataFrame)
    assert not buildings.empty, "Should fetch at least some buildings in Amsterdam center"
    assert buildings.crs.to_string() == "EPSG:28992"
    assert all(buildings.geometry.is_valid)


@pytest.mark.slow
def test_fetch_real_pvgis_data():
    """Integration test: fetch real solar data from PVGIS (slow)."""
    client = PVGISPVCalcClient()
    
    # Single point in Amsterdam
    result = client._fetch_point(lat=52.370, lon=4.895)
    
    assert result is not None
    assert 'outputs' in result
    assert 'totals' in result['outputs']
    
    e_y = result['outputs']['totals']['fixed']['E_y']
    assert isinstance(e_y, (int, float))
    assert 800 < e_y < 1300, "Annual solar energy in Amsterdam should be 800-1300 kWh/kWp"


# ============================================================
# Parametrized Tests
# ============================================================

@pytest.mark.parametrize("bbox,expected_crs", [
    ((4.88, 52.36, 4.89, 52.37), "EPSG:28992"),
    ((4.90, 52.35, 4.91, 52.36), "EPSG:28992"),
])
def test_fetch_pdok_buildings_returns_correct_crs(bbox, expected_crs):
    """Test that buildings are always returned in EPSG:28992."""
    buildings = fetch_pdok_buildings(bbox, output_path=None, page_size=10)
    assert buildings.crs.to_string() == expected_crs


@pytest.mark.parametrize("peakpower,loss", [
    (1, 14),
    (2, 10),
    (5, 20),
])
def test_pvgis_client_different_params(peakpower, loss):
    """Test PVGISPVCalcClient with different parameters."""
    client = PVGISPVCalcClient(peakpower=peakpower, loss=loss)
    
    assert client.peakpower == peakpower
    assert client.loss == loss
