# Data Acquisition Guide

## Overview
The data acquisition module uses **PDOK BAG3D WFS API** (Basisregistraties Adressen en Gebouwen 3D) as the primary data source for buildings in the Netherlands.

## Data Sources

### 1. **Building Data: PDOK BAG3D WFS**
- **Source**: PDOK BAG3D LoD1.2 buildings via WFS 2.0.0 API
- **Endpoint**: `https://data.3dbag.nl/api/BAG3D/wfs`
- **Coverage**: Netherlands only
- **Benefits**:
  - Roof height data (min, max, median)
  - Ground height for accurate building heights
  - Accurate footprint geometries
  - Official Dutch building registry data

### 2. **Building Attributes**
Each building includes:
- `identificatie`: Unique BAG identifier
- `b3_h_min`, `b3_h_max`, `b3_h_median`: Building heights (m above ground)
- `b3_h_dak_min`, `b3_h_dak_max`, `b3_h_dak_50p`, `b3_h_dak_70p`, `b3_h_dak_99p`: Roof height percentiles
- `b3_dak_type`: Roof type (e.g., slant, flat)
- `b3_kas_warenhuis`: Greenhouse/warehouse flag
- `geometry`: Polygon geometry in EPSG:28992 (RD New)

## Solar Data Assignment

### The Problem
Solar data from PVGIS API returns **point-based** values (lat/lon coordinates), but buildings are **polygons**. 

### The Solution: SciPy Griddata Interpolation
The module uses **SciPy's `griddata`** for spatial interpolation:

1. **Fetch Solar Grid**: Query PVGIS API for solar data points across the study area
2. **Convert to Arrays**: Extract coordinates and values from solar points
3. **Interpolate**: For each building centroid, use `griddata` to interpolate
4. **Methods**: Linear (default), cubic, or nearest neighbor interpolation
5. **Fallback**: If point is outside convex hull, automatically use nearest neighbor

### Interpolation Methods
- **Linear**: Fast, smooth, works inside convex hull
- **Cubic**: Smoother results, higher accuracy, slower
- **Nearest**: Fallback for points outside data coverage

## Usage

### Basic Usage
```python
from src.data_acquisition import fetch_pdok_buildings

# Amsterdam area (WGS84)
bbox = (4.8, 52.3, 5.0, 52.5)  # (min_lon, min_lat, max_lon, max_lat)

# Fetch buildings
buildings = fetch_pdok_buildings(
    area=bbox,
    output_path="buildings.geojson",
    page_size=1000
)

print(f"Fetched {len(buildings)} buildings")
```

### Step-by-Step with Solar Interpolation
```python
from src.data_acquisition import fetch_pdok_buildings, fetch_pvgis_solar
from src.geometry import interpolate_solar_at_point
import numpy as np
import geopandas as gpd

# 1. Get buildings
buildings = fetch_pdok_buildings(bbox)

# 2. Create solar sampling grid
lons = np.linspace(bbox[0], bbox[2], 10)  # 10 points longitude
lats = np.linspace(bbox[1], bbox[3], 10)  # 10 points latitude

# 3. Fetch solar data
solar_data = []
for lat in lats:
    for lon in lons:
        result = fetch_pvgis_solar(lat, lon)
        if result:
            solar_data.append({'lat': lat, 'lon': lon, 'energy': result['E_y']})

solar_gdf = gpd.GeoDataFrame(solar_data, 
    geometry=gpd.points_from_xy([d['lon'] for d in solar_data], 
                                  [d['lat'] for d in solar_data]),
    crs='EPSG:4326')

# 4. Interpolate to building centroids
buildings_wgs84 = buildings.to_crs('EPSG:4326')
solar_coords = np.array([[p.x, p.y] for p in solar_gdf.geometry])
solar_values = solar_gdf['energy'].values

buildings['solar_irradiance'] = buildings_wgs84.geometry.centroid.apply(
    lambda pt: interpolate_solar_at_point(pt, solar_coords, solar_values, method='linear')
)
```

## Key Functions

### `fetch_pdok_buildings(area, output_path, page_size=1000)`
Fetch buildings from PDOK BAG3D WFS API with automatic paging.

**Parameters:**
- `area`: Bounding box (min_lon, min_lat, max_lon, max_lat) in EPSG:4326, or GeoDataFrame, or file path
- `output_path`: Optional path to save GeoJSON output
- `page_size`: Number of features per request (default 1000)

**Returns:** GeoDataFrame in EPSG:28992 with BAG3D attributes

### `fetch_pvgis_solar(lat, lon, timeout=30)`
Fetch solar irradiance data from PVGIS API for a point location.

**Parameters:**
- `lat`: Latitude in WGS84
- `lon`: Longitude in WGS84
- `timeout`: Request timeout in seconds

**Returns:** Dictionary with solar data (E_y, E_m, E_d, H_sun, etc.)

### `interpolate_solar_at_point(point, solar_coords, solar_values, method='linear')`
*(from `geometry.py`)* Interpolate solar values to a building centroid using SciPy griddata.

**Parameters:**
- `point`: Shapely Point (building centroid)
- `solar_coords`: Array of solar point coordinates (N, 2)
- `solar_values`: Array of solar values (N,)
- `method`: 'linear', 'cubic', or 'nearest'

**Returns:** Interpolated solar energy value (kWh/m²/year)

## Solar Grid Sampling Guidelines

| Grid Points | Spacing | Use Case | API Calls |
|-------------|---------|----------|------------|
| 5×5 | ~varies | Small area, quick test | 25 |
| 10×10 | ~varies | Balanced, city district | 100 |
| 15×15 | ~varies | High accuracy | 225 |
| 20×20 | ~varies | Very detailed | 400 |

**Note:** Spacing depends on bounding box size. Use fewer points for quick testing to avoid PVGIS API rate limits.

## Example Workflow

```python
# Define study area (Amsterdam city center)
bbox = (4.88, 52.36, 4.91, 52.38)

# Fetch buildings
buildings = fetch_pdok_buildings(bbox, output_path='data/footprints.json')

# Convert to WGS84 for solar operations
buildings_wgs84 = buildings.to_crs('EPSG:4326')

# Now you can:
# - Calculate geometry from building polygons
# - Access height data: buildings['b3_h_max']
# - Get roof types: buildings['b3_dak_type']
# - Interpolate solar data using geometry.interpolate_solar_at_point()

print(f"Fetched {len(buildings)} buildings")
print(buildings[['identificatie', 'b3_h_max', 'b3_dak_type']].head())
```

## Dependencies
All required packages are in `requirements.txt`:
- `geopandas`: Spatial data handling and WFS queries
- `scipy`: Griddata interpolation
- `numpy`: Numerical operations
- `shapely`: Geometry operations
- `requests`: PVGIS API calls
- `pyproj`: Coordinate transformations

## Notes
- PDOK BAG3D covers the **Netherlands only**
- Native CRS is EPSG:28992 (RD New), converted to EPSG:4326 for solar operations
- PVGIS API has rate limits - use appropriate solar grid resolution
- SciPy griddata assumes smooth variation; use finer grids in complex terrain
- WFS paging handles large areas automatically (page_size=1000 default)
