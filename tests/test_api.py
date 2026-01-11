"""
Unit tests for REST API endpoints.
"""

import pytest
from src.api import app


@pytest.fixture
def client():
    """Create test client for Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_home_endpoint(client):
    """Test API home endpoint."""
    response = client.get('/')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'name' in data
    assert 'version' in data
    assert 'endpoints' in data


def test_buildings_endpoint(client):
    """Test buildings listing endpoint."""
    response = client.get('/buildings')
    assert response.status_code == 200


def test_buildings_with_filters(client):
    """Test buildings endpoint with query parameters."""
    response = client.get('/buildings?min_score=80&limit=50')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'buildings' in data
    assert 'total' in data
    assert 'count' in data
    assert 'limit' in data
    assert data['limit'] == 50


def test_building_detail_endpoint(client):
    """Test individual building detail endpoint."""
    response = client.get('/buildings/12345')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'identificatie' in data or 'fid' in data
    assert 'suitability_score' in data
    assert 'centroid' in data


def test_building_suitability_endpoint(client):
    """Test building suitability analysis endpoint."""
    response = client.get('/buildings/12345/suitability')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'suitability_score' in data
    assert 'energy_potential_kwh' in data
    assert 'category' in data


def test_priority_endpoint(client):
    """Test priority list endpoint."""
    response = client.get('/priority?top_n=10')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'priority_buildings' in data or 'buildings' in data


def test_404_error(client):
    """Test 404 error handling."""
    response = client.get('/nonexistent')
    assert response.status_code == 404
    
    data = response.get_json()
    assert 'error' in data
