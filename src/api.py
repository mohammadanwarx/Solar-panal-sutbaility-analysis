"""
REST API Module
Provides a geodata service for querying solar suitability results.
"""

import os
import json
from pathlib import Path
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import geopandas as gpd
import pandas as pd
from typing import Dict, Any, Optional

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Global data storage
buildings_data: Optional[gpd.GeoDataFrame] = None
DATA_PATH = Path("data")


def load_buildings_data():
    """Load processed buildings data on startup."""
    global buildings_data
    
    # Try to load ranked buildings first (most complete dataset)
    data_files = [
        DATA_PATH / "ranked_buildings.json",
        DATA_PATH / "buildings_with_solar_analysis.json",
        DATA_PATH / "processed_buildings.json",
        DATA_PATH / "ranked_test_buildings.json"  # Fallback to test data
    ]
    
    for data_file in data_files:
        if data_file.exists():
            try:
                buildings_data = gpd.read_file(data_file)
                print(f"✓ Loaded {len(buildings_data)} buildings from {data_file}")
                return True
            except Exception as e:
                print(f"✗ Failed to load {data_file}: {e}")
                continue
    
    print("⚠ No buildings data found. API will return empty results.")
    buildings_data = gpd.GeoDataFrame()
    return False


# Load data when module is imported
load_buildings_data()


@app.route('/')
def home():
    """API home endpoint with documentation."""
    return jsonify({
        "name": "Solar Panel Suitability API",
        "version": "0.1.0",
        "description": "REST API for querying solar panel suitability analysis results",
        "data_loaded": buildings_data is not None and len(buildings_data) > 0,
        "total_buildings": len(buildings_data) if buildings_data is not None else 0,
        "endpoints": {
            "/": "API documentation (this page)",
            "/health": "Health check endpoint",
            "/buildings": "Get all buildings with suitability scores (supports filtering)",
            "/buildings/<id>": "Get specific building details by ID",
            "/buildings/<id>/suitability": "Get detailed suitability analysis for a building",
            "/buildings/<id>/geojson": "Get building geometry as GeoJSON",
            "/priority": "Get priority list of top suitable buildings",
            "/stats": "Get summary statistics of the dataset",
            "/map/geojson": "Export filtered buildings as GeoJSON for mapping"
        },
        "query_parameters": {
            "/buildings": {
                "min_score": "Minimum suitability score (0-100)",
                "max_score": "Maximum suitability score (0-100)",
                "min_area": "Minimum roof area (m²)",
                "min_energy": "Minimum energy potential (kWh)",
                "category": "Suitability category (Excellent, Good, Moderate, Poor, Unsuitable)",
                "limit": "Maximum number of results",
                "offset": "Offset for pagination"
            },
            "/priority": {
                "top_n": "Number of top buildings to return (default 100)"
            }
        }
    })


@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "data_loaded": buildings_data is not None and len(buildings_data) > 0,
        "buildings_count": len(buildings_data) if buildings_data is not None else 0
    })


@app.route('/buildings', methods=['GET'])
def get_buildings():
    """
    Get all buildings with basic information.
    
    Query parameters:
    - min_score: Minimum suitability score (0-100)
    - max_score: Maximum suitability score (0-100)
    - min_area: Minimum roof area (m²)
    - min_energy: Minimum energy potential (kWh)
    - category: Suitability category
    - limit: Maximum number of results (default 100)
    - offset: Offset for pagination (default 0)
    """
    if buildings_data is None or len(buildings_data) == 0:
        return jsonify({"error": "No data loaded", "buildings": []}), 404
    
    # Get query parameters
    min_score = request.args.get('min_score', type=float)
    max_score = request.args.get('max_score', type=float)
    min_area = request.args.get('min_area', type=float)
    min_energy = request.args.get('min_energy', type=float)
    category = request.args.get('category', type=str)
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Filter data
    filtered = buildings_data.copy()
    
    if min_score is not None and 'suitability_score' in filtered.columns:
        filtered = filtered[filtered['suitability_score'] >= min_score]
    
    if max_score is not None and 'suitability_score' in filtered.columns:
        filtered = filtered[filtered['suitability_score'] <= max_score]
    
    if min_area is not None and 'roof_area_m2' in filtered.columns:
        filtered = filtered[filtered['roof_area_m2'] >= min_area]
    
    if min_energy is not None and 'solar_potential_kwh' in filtered.columns:
        filtered = filtered[filtered['solar_potential_kwh'] >= min_energy]
    
    if category and 'category' in filtered.columns:
        filtered = filtered[filtered['category'] == category]
    
    # Apply pagination
    total_results = len(filtered)
    filtered = filtered.iloc[offset:offset+limit]
    
    # Convert to dict (exclude geometry for performance)
    results = []
    for idx, row in filtered.iterrows():
        building = row.to_dict()
        # Remove geometry from response
        if 'geometry' in building:
            del building['geometry']
        results.append(building)
    
    return jsonify({
        "total": total_results,
        "limit": limit,
        "offset": offset,
        "count": len(results),
        "buildings": results
    })


@app.route('/buildings/<building_id>', methods=['GET'])
def get_building(building_id: str):
    """Get detailed information for a specific building."""
    if buildings_data is None or len(buildings_data) == 0:
        return jsonify({"error": "No data loaded"}), 404
    
    # Try to find building by ID or index
    building = None
    
    # Try by building_id column if exists
    if 'building_id' in buildings_data.columns:
        matches = buildings_data[buildings_data['building_id'].astype(str) == building_id]
        if len(matches) > 0:
            building = matches.iloc[0]
    
    # Try by index
    if building is None:
        try:
            idx = int(building_id)
            if 0 <= idx < len(buildings_data):
                building = buildings_data.iloc[idx]
        except ValueError:
            pass
    
    if building is None:
        return jsonify({"error": f"Building {building_id} not found"}), 404
    
    # Convert to dict
    result = building.to_dict()
    
    # Remove geometry, add centroid
    if 'geometry' in result:
        centroid = building.geometry.centroid
        result['centroid'] = {"lon": centroid.x, "lat": centroid.y}
        del result['geometry']
    
    return jsonify(result)


@app.route('/buildings/<building_id>/suitability', methods=['GET'])
def get_building_suitability(building_id: str):
    """
    Get solar panel suitability analysis for a specific building.
    
    Returns:
    - suitability_score: Overall score (0-100)
    - category: Suitability category
    - energy_potential_kwh: Annual energy production
    - roof_area_m2: Usable roof area
    - solar_irradiance: Solar irradiance value
    - shading_factor: Shading impact (0-1)
    - roof_orientation_deg: Roof orientation in degrees
    - annual_savings_eur: Annual cost savings
    - payback_period_years: Investment payback period
    """
    if buildings_data is None or len(buildings_data) == 0:
        return jsonify({"error": "No data loaded"}), 404
    
    # Find building
    building = None
    if 'building_id' in buildings_data.columns:
        matches = buildings_data[buildings_data['building_id'].astype(str) == building_id]
        if len(matches) > 0:
            building = matches.iloc[0]
    
    if building is None:
        try:
            idx = int(building_id)
            if 0 <= idx < len(buildings_data):
                building = buildings_data.iloc[idx]
        except ValueError:
            pass
    
    if building is None:
        return jsonify({"error": f"Building {building_id} not found"}), 404
    
    # Extract suitability metrics
    suitability = {
        "building_id": building_id,
        "suitability_score": float(building.get('suitability_score', 0)),
        "category": str(building.get('category', 'Unknown')),
        "energy_potential_kwh": float(building.get('solar_potential_kwh', 0)),
        "roof_area_m2": float(building.get('roof_area_m2', 0)),
        "solar_irradiance": float(building.get('solar_irradiance', 0)),
        "shading_factor": float(building.get('shading_factor', 0)),
        "roof_orientation_deg": float(building.get('roof_orientation_deg', 0)),
        "annual_savings_eur": float(building.get('annual_savings_eur', 0)),
        "payback_period_years": float(building.get('payback_period_years', 0))
    }
    
    return jsonify(suitability)


@app.route('/buildings/<building_id>/geojson', methods=['GET'])
def get_building_geojson(building_id: str):
    """Get building geometry as GeoJSON."""
    if buildings_data is None or len(buildings_data) == 0:
        return jsonify({"error": "No data loaded"}), 404
    
    # Find building
    building = None
    if 'building_id' in buildings_data.columns:
        matches = buildings_data[buildings_data['building_id'].astype(str) == building_id]
        if len(matches) > 0:
            building = matches.iloc[0:1]  # Keep as GeoDataFrame
    
    if building is None or len(building) == 0:
        try:
            idx = int(building_id)
            if 0 <= idx < len(buildings_data):
                building = buildings_data.iloc[idx:idx+1]
        except ValueError:
            pass
    
    if building is None or len(building) == 0:
        return jsonify({"error": f"Building {building_id} not found"}), 404
    
    # Convert to GeoJSON
    geojson = json.loads(building.to_json())
    
    return jsonify(geojson)


@app.route('/priority', methods=['GET'])
def get_priority_list():
    """
    Get priority list of buildings for solar panel installation.
    
    Query parameters:
    - top_n: Number of top buildings to return (default 100)
    """
    if buildings_data is None or len(buildings_data) == 0:
        return jsonify({"error": "No data loaded", "buildings": []}), 404
    
    top_n = request.args.get('top_n', 100, type=int)
    top_n = min(top_n, len(buildings_data))  # Cap at available buildings
    
    # Sort by suitability score
    if 'suitability_score' in buildings_data.columns:
        sorted_buildings = buildings_data.sort_values('suitability_score', ascending=False)
    elif 'rank' in buildings_data.columns:
        sorted_buildings = buildings_data.sort_values('rank', ascending=True)
    else:
        sorted_buildings = buildings_data
    
    top_buildings = sorted_buildings.head(top_n)
    
    # Convert to list
    results = []
    for i, (idx, row) in enumerate(top_buildings.iterrows(), start=1):
        building = {
            "rank": int(row.get('rank', i)),
            "building_id": str(row.get('building_id', idx)),
            "suitability_score": float(row.get('suitability_score', 0)),
            "category": str(row.get('category', 'Unknown')),
            "roof_area_m2": float(row.get('roof_area_m2', 0)),
            "energy_potential_kwh": float(row.get('solar_potential_kwh', 0)),
            "payback_years": float(row.get('payback_period_years', 0))
        }
        
        # Add centroid
        if hasattr(row, 'geometry') and row.geometry is not None:
            centroid = row.geometry.centroid
            building['centroid'] = {"lon": centroid.x, "lat": centroid.y}
        
        results.append(building)
    
    return jsonify({
        "total_buildings": len(buildings_data),
        "top_n": top_n,
        "count": len(results),
        "buildings": results
    })


@app.route('/stats', methods=['GET'])
def get_statistics():
    """Get summary statistics of the dataset."""
    if buildings_data is None or len(buildings_data) == 0:
        return jsonify({"error": "No data loaded"}), 404
    
    stats = {
        "total_buildings": len(buildings_data),
        "columns": list(buildings_data.columns)
    }
    
    # Calculate statistics for numeric columns
    numeric_cols = ['suitability_score', 'roof_area_m2', 'solar_potential_kwh', 
                    'solar_irradiance', 'shading_factor', 'payback_period_years']
    
    for col in numeric_cols:
        if col in buildings_data.columns:
            stats[col] = {
                "mean": float(buildings_data[col].mean()),
                "median": float(buildings_data[col].median()),
                "min": float(buildings_data[col].min()),
                "max": float(buildings_data[col].max()),
                "std": float(buildings_data[col].std())
            }
    
    # Category distribution
    if 'category' in buildings_data.columns:
        stats['category_distribution'] = buildings_data['category'].value_counts().to_dict()
    
    return jsonify(stats)


@app.route('/map/geojson', methods=['GET'])
def export_geojson():
    """
    Export filtered buildings as GeoJSON for mapping.
    
    Supports same filters as /buildings endpoint.
    """
    if buildings_data is None or len(buildings_data) == 0:
        return jsonify({"error": "No data loaded"}), 404
    
    # Get query parameters (same as /buildings)
    min_score = request.args.get('min_score', type=float)
    max_score = request.args.get('max_score', type=float)
    category = request.args.get('category', type=str)
    limit = request.args.get('limit', 1000, type=int)
    
    # Filter data
    filtered = buildings_data.copy()
    
    if min_score is not None and 'suitability_score' in filtered.columns:
        filtered = filtered[filtered['suitability_score'] >= min_score]
    
    if max_score is not None and 'suitability_score' in filtered.columns:
        filtered = filtered[filtered['suitability_score'] <= max_score]
    
    if category and 'category' in filtered.columns:
        filtered = filtered[filtered['category'] == category]
    
    # Apply limit
    filtered = filtered.head(limit)
    
    # Convert to GeoJSON
    geojson = json.loads(filtered.to_json())
    
    return jsonify(geojson)


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error", "message": str(error)}), 500


def main():
    """Main entry point for the API."""
    print("=" * 70)
    print("SOLAR PANEL SUITABILITY API")
    print("=" * 70)
    
    # Load data
    load_buildings_data()
    
    # Run server
    print("\nStarting API server...")
    print("API Documentation: http://localhost:5000/")
    print("=" * 70)
    
    app.run(host='0.0.0.0', port=5000, debug=True)


if __name__ == '__main__':
    main()
