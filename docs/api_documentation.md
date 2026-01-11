# Solar Panel Suitability API Documentation

Version: 0.1.0

## Overview

The Solar Panel Suitability API provides programmatic access to solar panel installation suitability analysis results for buildings. Query individual buildings, get priority lists, export GeoJSON for mapping, and access comprehensive statistics.

**Base URL:** `http://localhost:5000`

**Technology Stack:** Flask + Flask-CORS + GeoPandas

---

## Quick Start

### Starting the API Server

```bash
# From project root
python src/api.py
```

The API will be available at `http://localhost:5000`

### Stopping the API Server

Press **`Ctrl + C`** in the terminal where the server is running, or:

```bash
# Kill the process
pkill -f api.py

# Or kill by port
fuser -k 5000/tcp
```

---

## Data Loading

The API automatically loads building data on startup from these files (in priority order):
1. `data/ranked_buildings.json` (most complete dataset)
2. `data/buildings_with_solar_analysis.json`
3. `data/processed_buildings.json`
4. `data/ranked_test_buildings.json` (fallback for testing)

---

## Endpoints

### 1. API Information & Health

#### `GET /`

Returns comprehensive API documentation, available endpoints, and data loading status.

**Response:**
```json
{
  "name": "Solar Panel Suitability API",
  "version": "0.1.0",
  "description": "REST API for querying solar panel suitability analysis results",
  "data_loaded": true,
  "total_buildings": 1523,
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
}
```

#### `GET /health`

Health check endpoint to verify API status and data availability.

**Response:**
```json
{
  "status": "healthy",
  "data_loaded": true,
  "buildings_count": 1523
}
```

---

### 2. List All Buildings

#### `GET /buildings`

Get a list of all buildings with comprehensive filtering and pagination support.

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `min_score` | float | No | - | Minimum suitability score (0-100) |
| `max_score` | float | No | - | Maximum suitability score (0-100) |
| `min_area` | float | No | - | Minimum roof area in m² |
| `min_energy` | float | No | - | Minimum energy potential in kWh/year |
| `category` | string | No | - | Suitability category: `Excellent`, `Good`, `Fair`, `Poor` |
| `limit` | integer | No | 100 | Maximum number of results to return |
| `offset` | integer | No | 0 | Offset for pagination |

**Example Requests:**
```bash
# Get all buildings (first 100)
curl "http://localhost:5000/buildings"

# Get buildings with high suitability
curl "http://localhost:5000/buildings?min_score=80"

# Get buildings in a score range
curl "http://localhost:5000/buildings?min_score=60&max_score=90"

# Get large buildings with good energy potential
curl "http://localhost:5000/buildings?min_area=200&min_energy=15000"

# Filter by category
curl "http://localhost:5000/buildings?category=Excellent"

# Pagination - get page 2 (results 20-40)
curl "http://localhost:5000/buildings?limit=20&offset=20"

# Combine multiple filters
curl "http://localhost:5000/buildings?min_score=70&min_area=150&category=Excellent&limit=50"
```

**Example Response:**
```json
{
  "total": 1523,
  "limit": 100,
  "offset": 0,
  "count": 100,
  "buildings": [
    {
      "building_id": "NL.IMBAG.Pand.12345",
      "identificatie": "NL.IMBAG.Pand.12345",
      "suitability_score": 92.5,
      "suitability_class": "Excellent",
      "roof_area": 250.8,
      "energy_potential": 18500,
      "orientation": 185.3,
      "shading_factor": 0.08,
      "h_dak_max": 12.5,
      "rank": 15
    }
  ]
}
```

**Notes:**
- Geometry is excluded from the response for performance
- Use `/buildings/<id>/geojson` to get geometry for specific buildings
- `total` shows the number of buildings matching filters (before pagination)

---

### 3. Get Building Details

#### `GET /buildings/<building_id>`

Get detailed information for a specific building by ID or index.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `building_id` | string/int | Yes | Building ID (e.g., `NL.IMBAG.Pand.12345`) or numeric index |

**Building ID Lookup:**
The API supports two ways to identify buildings:
1. **Building ID column** - Searches the `building_id` or `identificatie` field
2. **Numeric index** - If an integer is provided, returns the building at that index position

**Example Requests:**
```bash
# By building ID
curl "http://localhost:5000/buildings/NL.IMBAG.Pand.12345"

# By index
curl "http://localhost:5000/buildings/0"
curl "http://localhost:5000/buildings/42"
```

**Example Response:**
```json
{
  "building_id": "NL.IMBAG.Pand.12345",
  "identificatie": "NL.IMBAG.Pand.12345",
  "roof_area": 250.8,
  "energy_potential": 18500,
  "suitability_score": 92.5,
  "suitability_class": "Excellent",
  "orientation": 185.3,
  "shading_factor": 0.08,
  "h_dak_max": 12.5,
  "rank": 15,
  "centroid": {
    "lon": 6.8856,
    "lat": 52.2198
  }
}
```

**Notes:**
- Geometry is removed from response; centroid coordinates are provided instead
- Use `/buildings/<id>/geojson` to get the full geometry

---

### 4. Get Building Suitability Analysis

#### `GET /buildings/<building_id>/suitability`

Get comprehensive solar panel suitability analysis for a specific building.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `building_id` | string/int | Yes | Building ID or numeric index |

**Example Request:**
```bash
curl "http://localhost:5000/buildings/NL.IMBAG.Pand.12345/suitability"
```

**Example Response:**
```json
{
  "building_id": "NL.IMBAG.Pand.12345",
  "suitability_score": 85.5,
  "category": "Excellent",
  "energy_potential_kwh": 18500,
  "roof_area_m2": 250.8,
  "solar_irradiance": 1050.0,
  "shading_factor": 0.08,
  "roof_orientation_deg": 185.3,
  "annual_savings_eur": 4625.0,
  "payback_period_years": 7.2
}
```

**Field Descriptions:**
| Field | Type | Description |
|-------|------|-------------|
| `suitability_score` | float | Overall suitability score (0-100) |
| `category` | string | Classification: Excellent, Good, Fair, Poor |
| `energy_potential_kwh` | float | Estimated annual energy production in kWh |
| `roof_area_m2` | float | Total roof area in square meters |
| `solar_irradiance` | float | Solar irradiance value (kWh/m²/year) |
| `shading_factor` | float | Shading impact (0=no shading, 1=fully shaded) |
| `roof_orientation_deg` | float | Roof orientation in degrees (180°=South) |
| `annual_savings_eur` | float | Estimated annual cost savings |
| `payback_period_years` | float | Investment payback period |

---

### 5. Get Building GeoJSON

#### `GET /buildings/<building_id>/geojson`

Get the building's geometry as GeoJSON format for mapping applications.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `building_id` | string/int | Yes | Building ID or numeric index |

**Example Request:**
```bash
curl "http://localhost:5000/buildings/NL.IMBAG.Pand.12345/geojson"
```

**Example Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "building_id": "NL.IMBAG.Pand.12345",
        "suitability_score": 92.5,
        "roof_area": 250.8,
        "energy_potential": 18500,
        "suitability_class": "Excellent"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [6.8850, 52.2195],
            [6.8855, 52.2195],
            [6.8855, 52.2198],
            [6.8850, 52.2198],
            [6.8850, 52.2195]
          ]
        ]
      }
    }
  ]
}
```

**Use Cases:**
- Display building footprint on web maps (Leaflet, Mapbox, Folium)
- Export individual building geometry
- Integration with GIS applications

---

### 6. Get Priority List

#### `GET /priority`

Get a priority-ranked list of buildings for solar panel installation, sorted by suitability score.

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `top_n` | integer | No | 100 | Number of top buildings to return |

**Example Requests:**
```bash
# Get top 10 buildings
curl "http://localhost:5000/priority?top_n=10"

# Get default top 100
curl "http://localhost:5000/priority"

# Get all buildings ranked
curl "http://localhost:5000/priority?top_n=9999"
```

**Example Response:**
```json
{
  "total_buildings": 1523,
  "top_n": 10,
  "count": 10,
  "buildings": [
    {
      "rank": 1,
      "building_id": "NL.IMBAG.Pand.98765",
      "suitability_score": 98.7,
      "category": "Excellent",
      "roof_area_m2": 450.2,
      "energy_potential_kwh": 35000,
      "payback_years": 5.8,
      "centroid": {
        "lon": 6.8912,
        "lat": 52.2234
      }
    },
    {
      "rank": 2,
      "building_id": "NL.IMBAG.Pand.54321",
      "suitability_score": 97.3,
      "category": "Excellent",
      "roof_area_m2": 380.5,
      "energy_potential_kwh": 32000,
      "payback_years": 6.1,
      "centroid": {
        "lon": 6.8889,
        "lat": 52.2201
      }
    }
  ]
}
```

**Sorting Logic:**
- Primary sort: `suitability_score` (descending)
- Fallback: `rank` column (ascending) if available

---

### 7. Get Summary Statistics

#### `GET /stats`

Get comprehensive summary statistics of the entire dataset.

**Example Request:**
```bash
curl "http://localhost:5000/stats"
```

**Example Response:**
```json
{
  "total_buildings": 1523,
  "columns": [
    "building_id",
    "roof_area",
    "suitability_score",
    "energy_potential",
    "shading_factor",
    "orientation",
    "suitability_class",
    "rank"
  ],
  "suitability_score": {
    "mean": 68.5,
    "median": 71.2,
    "min": 12.3,
    "max": 98.7,
    "std": 18.9
  },
  "roof_area_m2": {
    "mean": 185.7,
    "median": 145.3,
    "min": 45.2,
    "max": 850.6,
    "std": 112.4
  },
  "solar_potential_kwh": {
    "mean": 12500,
    "median": 9800,
    "min": 1200,
    "max": 45000,
    "std": 8900
  },
  "shading_factor": {
    "mean": 0.185,
    "median": 0.15,
    "min": 0.0,
    "max": 0.85,
    "std": 0.12
  },
  "payback_period_years": {
    "mean": 8.5,
    "median": 7.8,
    "min": 4.2,
    "max": 18.5,
    "std": 3.2
  },
  "category_distribution": {
    "Excellent": 234,
    "Good": 589,
    "Fair": 512,
    "Poor": 188
  }
}
```

**Statistics Provided:**
- **mean**: Average value
- **median**: Middle value (50th percentile)
- **min**: Minimum value
- **max**: Maximum value
- **std**: Standard deviation (measure of spread)

---

### 8. Export Map GeoJSON

#### `GET /map/geojson`

Export filtered buildings as GeoJSON for use in mapping applications (Leaflet, Mapbox, QGIS, etc.).

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `min_score` | float | No | - | Minimum suitability score (0-100) |
| `max_score` | float | No | - | Maximum suitability score (0-100) |
| `category` | string | No | - | Filter by suitability category |
| `limit` | integer | No | 1000 | Maximum number of buildings to export |

**Example Requests:**
```bash
# Export all excellent buildings
curl "http://localhost:5000/map/geojson?category=Excellent"

# Export buildings with score >= 80
curl "http://localhost:5000/map/geojson?min_score=80"

# Export buildings in a score range
curl "http://localhost:5000/map/geojson?min_score=60&max_score=90&limit=500"

# Save to file
curl "http://localhost:5000/map/geojson?min_score=70" > buildings.geojson
```

**Example Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "building_id": "NL.IMBAG.Pand.12345",
        "suitability_score": 92.5,
        "suitability_class": "Excellent",
        "roof_area": 250.8,
        "energy_potential": 18500,
        "shading_factor": 0.08,
        "orientation": 185.3,
        "rank": 15
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[6.8850, 52.2195], [6.8855, 52.2195], [6.8855, 52.2198], [6.8850, 52.2198], [6.8850, 52.2195]]]
      }
    }
  ]
}
```

**Use Cases:**
- Create choropleth maps colored by suitability
- Export data for GIS analysis
- Web mapping integration
- Download filtered datasets

---

## Status Codes

| Code | Description |
|------|-------------|
| 200 | Success - Request completed successfully |
| 400 | Bad Request - Invalid parameters provided |
| 404 | Not Found - Resource does not exist or no data loaded |
| 500 | Internal Server Error - Server encountered an error |

---

## Error Response Format

All error responses follow this format:

```json
{
  "error": "Building NL.IMBAG.Pand.99999 not found"
}
```

Or for data loading errors:

```json
{
  "error": "No data loaded",
  "buildings": []
}
```

---

## Running the API

### Development Server

```bash
# From project root
cd /home/valonyando/ITC/ScProg/G1/ITC-Solar-Panel-Suitability-Mapping
python src/api.py
```

**Output:**
```
======================================================================
SOLAR PANEL SUITABILITY API
======================================================================
✓ Loaded 1523 buildings from data/ranked_buildings.json

Starting API server...
API Documentation: http://localhost:5000/
======================================================================
 * Serving Flask app 'api'
 * Debug mode: on
 * Running on http://0.0.0.0:5000
```

### Stopping the Server

Press **`Ctrl + C`** in the terminal, or:

```bash
# Kill by process name
pkill -f api.py

# Kill by port
fuser -k 5000/tcp

# Find and kill specific process
ps aux | grep api.py
kill <PID>
```

### Production Deployment

For production use, deploy with a production WSGI server:

```bash
# Install gunicorn
pip install gunicorn

# Run with 4 worker processes
gunicorn -w 4 -b 0.0.0.0:5000 src.api:app

# Or with better configuration
gunicorn -w 4 \
  --timeout 120 \
  --access-logfile access.log \
  --error-logfile error.log \
  -b 0.0.0.0:5000 \
  src.api:app
```

**Docker Deployment:**

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ src/
COPY data/ data/

EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "src.api:app"]
```

---

## CORS Configuration

The API has **CORS (Cross-Origin Resource Sharing) enabled** by default, allowing requests from web browsers on different domains.

This enables:
- Web-based dashboards and mapping applications
- JavaScript fetch/axios requests from any origin
- Integration with frontend frameworks (React, Vue, Angular)

To restrict CORS in production:

```python
from flask_cors import CORS

# Only allow specific origins
CORS(app, origins=["https://yourdomain.com"])
```

---

## Security Considerations

### Current Implementation

⚠️ **This is a development API with no authentication or rate limiting.**

### Production Recommendations

1. **Authentication**
   - Implement API key authentication
   - Use OAuth 2.0 for user-based access
   - Add JWT tokens for secure sessions

2. **Rate Limiting**
   ```bash
   pip install flask-limiter
   ```
   
   ```python
   from flask_limiter import Limiter
   
   limiter = Limiter(app, key_func=lambda: request.remote_addr)
   
   @app.route('/buildings')
   @limiter.limit("100 per minute")
   def get_buildings():
       ...
   ```

3. **HTTPS**
   - Deploy behind nginx or Apache with SSL/TLS
   - Use Let's Encrypt for free certificates

4. **Input Validation**
   - Validate all query parameters
   - Sanitize building IDs to prevent injection

---

## Usage Examples

### Python (requests)

```python
import requests

# Base URL
BASE_URL = "http://localhost:5000"

# 1. Check API health
response = requests.get(f"{BASE_URL}/health")
print(response.json())

# 2. Get buildings with high suitability
response = requests.get(
    f"{BASE_URL}/buildings",
    params={
        'min_score': 80,
        'min_area': 200,
        'limit': 50
    }
)
buildings = response.json()['buildings']

# 3. Get specific building details
building_id = "NL.IMBAG.Pand.12345"
response = requests.get(f"{BASE_URL}/buildings/{building_id}")
building = response.json()

# 4. Get suitability analysis
response = requests.get(f"{BASE_URL}/buildings/{building_id}/suitability")
analysis = response.json()
print(f"Energy potential: {analysis['energy_potential_kwh']} kWh/year")
print(f"Payback period: {analysis['payback_period_years']} years")

# 5. Get priority list
response = requests.get(f"{BASE_URL}/priority", params={'top_n': 10})
top_10 = response.json()['buildings']

for building in top_10:
    print(f"Rank {building['rank']}: Score {building['suitability_score']}")

# 6. Get statistics
response = requests.get(f"{BASE_URL}/stats")
stats = response.json()
print(f"Total buildings: {stats['total_buildings']}")
print(f"Average score: {stats['suitability_score']['mean']:.2f}")

# 7. Export GeoJSON
response = requests.get(
    f"{BASE_URL}/map/geojson",
    params={'min_score': 70, 'limit': 500}
)
geojson_data = response.json()

# Save to file
import json
with open('buildings.geojson', 'w') as f:
    json.dump(geojson_data, f)
```

### JavaScript (fetch)

```javascript
const BASE_URL = 'http://localhost:5000';

// Get buildings with filtering
async function getBuildings() {
  const params = new URLSearchParams({
    min_score: 80,
    limit: 50
  });
  
  const response = await fetch(`${BASE_URL}/buildings?${params}`);
  const data = await response.json();
  
  console.log(`Found ${data.count} buildings`);
  return data.buildings;
}

// Get building suitability
async function getBuildingSuitability(buildingId) {
  const response = await fetch(`${BASE_URL}/buildings/${buildingId}/suitability`);
  const analysis = await response.json();
  
  console.log(`Suitability score: ${analysis.suitability_score}`);
  console.log(`Energy potential: ${analysis.energy_potential_kwh} kWh/year`);
  
  return analysis;
}

// Get top priority buildings
async function getTopBuildings(n = 10) {
  const response = await fetch(`${BASE_URL}/priority?top_n=${n}`);
  const data = await response.json();
  
  data.buildings.forEach(building => {
    console.log(`Rank ${building.rank}: ${building.building_id} (Score: ${building.suitability_score})`);
  });
  
  return data.buildings;
}

// Load GeoJSON for mapping
async function loadMapData() {
  const response = await fetch(`${BASE_URL}/map/geojson?min_score=70`);
  const geojson = await response.json();
  
  // Use with Leaflet or Mapbox
  // L.geoJSON(geojson).addTo(map);
  
  return geojson;
}

// Usage
getBuildings();
getBuildingSuitability('NL.IMBAG.Pand.12345');
getTopBuildings(10);
loadMapData();
```

### cURL Examples

```bash
# 1. API information
curl http://localhost:5000/

# 2. Health check
curl http://localhost:5000/health

# 3. Get buildings with filters
curl "http://localhost:5000/buildings?min_score=80&limit=20"

# 4. Get specific building
curl http://localhost:5000/buildings/NL.IMBAG.Pand.12345

# 5. Get suitability analysis
curl http://localhost:5000/buildings/0/suitability

# 6. Get building geometry
curl http://localhost:5000/buildings/0/geojson

# 7. Get top 10 priority buildings
curl "http://localhost:5000/priority?top_n=10"

# 8. Get statistics
curl http://localhost:5000/stats

# 9. Export GeoJSON with filters
curl "http://localhost:5000/map/geojson?category=Excellent" > excellent_buildings.geojson

# 10. Formatted JSON output
curl -s http://localhost:5000/priority?top_n=5 | jq .

# 11. Extract specific fields
curl -s http://localhost:5000/buildings?limit=10 | jq '.buildings[] | {id: .building_id, score: .suitability_score}'

# 12. Get count of excellent buildings
curl -s "http://localhost:5000/buildings?category=Excellent&limit=9999" | jq '.count'
```

### R Example

```r
library(httr)
library(jsonlite)

# Base URL
base_url <- "http://localhost:5000"

# Get buildings
response <- GET(
  paste0(base_url, "/buildings"),
  query = list(min_score = 80, limit = 100)
)

buildings <- content(response, as = "parsed")
df <- as.data.frame(do.call(rbind, buildings$buildings))

# Get statistics
response <- GET(paste0(base_url, "/stats"))
stats <- content(response, as = "parsed")

print(paste("Total buildings:", stats$total_buildings))
print(paste("Average score:", stats$suitability_score$mean))

# Plot distribution
hist(as.numeric(df$suitability_score), 
     main = "Suitability Score Distribution",
     xlab = "Score")
```

---

## Integration Examples

### Leaflet Web Map

```html
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
</head>
<body>
  <div id="map" style="height: 600px;"></div>
  
  <script>
    // Create map
    const map = L.map('map').setView([52.22, 6.89], 14);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
    
    // Load buildings from API
    fetch('http://localhost:5000/map/geojson?min_score=70')
      .then(response => response.json())
      .then(data => {
        // Color by suitability
        L.geoJSON(data, {
          style: function(feature) {
            const score = feature.properties.suitability_score;
            return {
              fillColor: score >= 80 ? '#00ff00' : 
                         score >= 60 ? '#ffff00' : '#ff0000',
              weight: 1,
              opacity: 1,
              fillOpacity: 0.6
            };
          },
          onEachFeature: function(feature, layer) {
            const props = feature.properties;
            layer.bindPopup(`
              <b>Building ${props.building_id}</b><br>
              Suitability: ${props.suitability_score.toFixed(1)}<br>
              Energy: ${props.energy_potential.toFixed(0)} kWh/year
            `);
          }
        }).addTo(map);
      });
  </script>
</body>
</html>
```

### Dashboard with Pandas

```python
import requests
import pandas as pd
import matplotlib.pyplot as plt

# Fetch all buildings
response = requests.get('http://localhost:5000/buildings', params={'limit': 9999})
data = response.json()

# Convert to DataFrame
df = pd.DataFrame(data['buildings'])

# Analysis
print(f"Total buildings: {len(df)}")
print(f"\nSuitability distribution:")
print(df['suitability_class'].value_counts())

# Visualizations
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# Score distribution
df['suitability_score'].hist(bins=30, ax=axes[0, 0])
axes[0, 0].set_title('Suitability Score Distribution')
axes[0, 0].set_xlabel('Score')

# Energy potential
df['energy_potential'].hist(bins=30, ax=axes[0, 1], color='orange')
axes[0, 1].set_title('Energy Potential Distribution')
axes[0, 1].set_xlabel('kWh/year')

# Roof area vs energy
axes[1, 0].scatter(df['roof_area'], df['energy_potential'], alpha=0.5)
axes[1, 0].set_xlabel('Roof Area (m²)')
axes[1, 0].set_ylabel('Energy Potential (kWh)')
axes[1, 0].set_title('Roof Area vs Energy Potential')

# Category counts
df['suitability_class'].value_counts().plot(kind='bar', ax=axes[1, 1])
axes[1, 1].set_title('Buildings by Category')
axes[1, 1].set_xlabel('Category')

plt.tight_layout()
plt.savefig('api_analysis.png', dpi=300)
plt.show()
```

---

## Troubleshooting

### API Won't Start

**Problem:** `Address already in use` error

**Solution:**
```bash
# Find process using port 5000
lsof -i :5000

# Kill the process
kill <PID>

# Or force kill all on port 5000
fuser -k 5000/tcp
```

### No Data Loaded

**Problem:** API returns `"data_loaded": false` or empty results

**Solution:**
1. Check that data files exist in the `data/` directory:
   ```bash
   ls -lh data/*.json
   ```

2. Verify data files are valid GeoJSON:
   ```bash
   head -n 20 data/ranked_buildings.json
   ```

3. Check console output when starting the API for loading errors

4. Run notebooks 01 and 02 to generate the required data files

### 404 Errors for Specific Buildings

**Problem:** Building not found by ID

**Solutions:**
- Try using numeric index instead: `/buildings/0`, `/buildings/42`
- Check available building IDs: `curl http://localhost:5000/buildings?limit=10`
- Verify building exists in the dataset: `curl http://localhost:5000/stats`

### CORS Errors in Browser

**Problem:** Browser blocks requests due to CORS policy

**Solution:** Already handled! The API has CORS enabled by default via `flask-cors`.

If still blocked, ensure you're accessing via `http://localhost:5000` not `http://127.0.0.1:5000` (or vice versa).

### Slow Response Times

**Solutions:**
1. Use pagination with `limit` parameter
2. Apply filters to reduce result set size
3. Exclude geometry from responses (already done for `/buildings`)
4. Use `/buildings/<id>/geojson` only when geometry is needed
5. For production, increase gunicorn workers

---

## API Limitations

| Aspect | Current Limit | Notes |
|--------|---------------|-------|
| Max results per request | 1000 (configurable) | Use pagination for more |
| Request timeout | 30 seconds | Default Flask timeout |
| Max concurrent connections | Limited by Flask dev server | Use gunicorn in production |
| Data refresh | Manual restart required | Reload data by restarting API |
| Geographic filtering | Not implemented | Filter after fetching or use GIS tools |
| Spatial queries | Not implemented | Use coordinate-based filtering in client |

---

## Future Enhancements

Potential features for future versions:

1. **Geographic Search**
   - Bounding box queries
   - Radius-based search from coordinates
   - Polygon intersection queries

2. **Advanced Filtering**
   - Filter by building type
   - Filter by construction year
   - Filter by neighborhood/district

3. **Aggregations**
   - Neighborhood-level statistics
   - Grid-based aggregations
   - Time-series projections

4. **Bulk Operations**
   - Batch building queries
   - Bulk updates via POST/PUT
   - CSV import/export

5. **Real-time Updates**
   - WebSocket support for live data
   - Automatic data refresh
   - Change notifications

6. **Extended Analysis**
   - Cost estimation calculator
   - ROI comparison tools
   - Installation scheduling API

---

## Support & Contributing

### Documentation

- **API Documentation:** This file
- **Data Acquisition Guide:** `docs/data_acquisition_guide.md`
- **Source Code:** `src/api.py`

### Issues & Questions

For bug reports, feature requests, or questions:
1. Check existing issues on GitHub
2. Create a new issue with detailed description
3. Include API version and error messages

### Testing the API

```bash
# Run health check
curl http://localhost:5000/health

# Test all endpoints
curl http://localhost:5000/
curl http://localhost:5000/buildings?limit=5
curl http://localhost:5000/buildings/0
curl http://localhost:5000/buildings/0/suitability
curl http://localhost:5000/buildings/0/geojson
curl http://localhost:5000/priority?top_n=5
curl http://localhost:5000/stats
curl http://localhost:5000/map/geojson?limit=10
```

---

## Version History

### Version 0.1.0 (Current)

**Features:**
- Building listing with filtering and pagination
- Individual building details and geometry
- Suitability analysis endpoint
- Priority ranking system
- Summary statistics
- GeoJSON export for mapping
- CORS support
- Comprehensive error handling

**Data Sources:**
- PDOK BAG3D building footprints
- PVGIS solar irradiance data
- Calculated suitability scores

---

## License

This API is part of the ITC Solar Panel Suitability Mapping project. See LICENSE file for details.

---

**Last Updated:** January 11, 2026  
**API Version:** 0.1.0  
**Maintainers:** ITC Group 3 - Val and Mo
