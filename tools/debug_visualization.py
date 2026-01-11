"""Quick debug script to validate buildings.geojson for MapLibre display.
Generates buildings_3d_debug_run.json with basic stats.
"""
import json
from pathlib import Path
import geopandas as gpd
from shapely.geometry import shape
import math

p = Path('buildings.geojson')
if not p.exists():
    print('ERROR: buildings.geojson not found in workspace root')
    raise SystemExit(1)

b = gpd.read_file(p)
print('Loaded buildings:', len(b))

# find height
candidates = ['b3_h_max','height','hoogte','building:height','roofHeight','z','maxh','hoogte_m','aantal_verdiepingen','floors']
height_col = next((c for c in candidates if c in b.columns), None)
print('Detected height column:', height_col)
if height_col is None:
    if 'aantal_verdiepingen' in b.columns:
        b['height'] = b['aantal_verdiepingen'].astype(float) * 3.0
        height_col = 'height'
    else:
        b['height'] = 8.0
        height_col = 'height'

# transform to 4326 if needed
if b.crs is not None and b.crs.to_epsg() != 4326:
    b = b.to_crs('EPSG:4326')
else:
    if b.crs is None:
        b = b.set_crs(epsg=4326, allow_override=True)

# Convert datetime-like columns to strings to avoid JSON serialization errors
import pandas as pd
for col in b.columns:
    if pd.api.types.is_datetime64_any_dtype(b[col]):
        b[col] = b[col].astype(str).replace('NaT', None)
    elif b[col].dtype == object:
        # object dtype may contain Timestamp instances
        if b[col].apply(lambda x: isinstance(x, pd.Timestamp) if x is not None else False).any():
            b[col] = b[col].astype(str).replace('NaT', None)

# basic validation
geojson = json.loads(b.to_json())
features = geojson.get('features', [])
valid = 0
dropped = 0
counts = {'Point':0,'LineString':0,'Polygon':0,'MultiPolygon':0,'Other':0}
for feat in features:
    try:
        s = shape(feat.get('geometry'))
        t = s.geom_type
        if t in counts:
            counts[t] += 1
        else:
            counts['Other'] += 1
        if s.is_empty:
            dropped += 1
            continue
        valid += 1
    except Exception:
        dropped += 1

print(f'total: {len(features)}, valid: {valid}, dropped: {dropped}')
print('geometry counts:', counts)

# serialize sample to check size
sample_geojson = {'type':'FeatureCollection','features':features[:200]}
size = len(json.dumps(sample_geojson).encode('utf-8'))
print('Sample (200) serialized size (bytes):', size)

# write debug file
Path('buildings_3d_debug_run.json').write_text(json.dumps({'total':len(features),'valid':valid,'dropped':dropped,'counts':counts,'sample_size_bytes':size}, indent=2))
print('Wrote buildings_3d_debug_run.json')

# --- Generate sample HTML (same logic as notebook) ---
SAMPLE_LIMIT = 200
sample_features = features[:SAMPLE_LIMIT]
sample_geojson = {'type': 'FeatureCollection', 'features': sample_features}
js_geojson = json.dumps(sample_geojson)
size_bytes = len(js_geojson.encode('utf-8'))

# Compute center from sample centroids
from shapely.geometry import shape
centroids = []
for feat in sample_features:
    try:
        s = shape(feat.get('geometry'))
        c = s.centroid
        if math.isfinite(c.x) and math.isfinite(c.y):
            centroids.append((c.x, c.y))
    except Exception:
        continue
if centroids:
    center_lon = sum(x for x, y in centroids) / len(centroids)
    center_lat = sum(y for x, y in centroids) / len(centroids)
else:
    bbox = b.total_bounds
    center_lon = float((bbox[0] + bbox[2]) / 2)
    center_lat = float((bbox[1] + bbox[3]) / 2)

html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <title>3D Buildings Extrusion (sample)</title>
  <meta name=\"viewport\" content=\"initial-scale=1,maximum-scale=1,user-scalable=no\" />
  <script src=\"https://unpkg.com/maplibre-gl@2.4.0/dist/maplibre-gl.js\"></script>
  <link href=\"https://unpkg.com/maplibre-gl@2.4.0/dist/maplibre-gl.css\" rel=\"stylesheet\" />
  <style>
    body {{ margin:0; padding:0; }}
    #map {{ position:absolute; top:0; bottom:0; width:100%; height:100vh; }}
    #info {{ position:absolute; left:10px; top:10px; z-index:1000; background:rgba(255,255,255,0.95); padding:8px; border-radius:6px; font-family:Arial; font-size:13px; }}
  </style>
</head>
<body>
<div id=\"info\">Features: {len(sample_features)} (sample) — center: {0},{0}<br>Serialized sample size: {size_bytes} bytes</div>
<div id=\"map\"></div>
<script>
function webglSupport() {{
  try {{
    var canvas = document.createElement('canvas');
    return !!window.WebGLRenderingContext && (canvas.getContext('webgl') || canvas.getContext('experimental-webgl'));
  }} catch (e) {{
    return false;
  }}
}}

(function() {{
  try {{
    const geojson = {js_geojson};
    console.log('Loaded geojson features:', geojson.features.length);

    const info = document.getElementById('info');
    info.innerHTML += '<br>WebGL supported: ' + (webglSupport() ? 'yes' : 'no');
    if (!webglSupport()) {{
      info.innerHTML += '<br><strong>Warning:</strong> WebGL not available — 3D extrusion requires WebGL.';
    }}

    const map = new maplibregl.Map({{
      container: 'map',
      style: 'https://demotiles.maplibre.org/style.json',
      center: [0,0],
      zoom: 15,
      pitch: 60,
      bearing: -17.6,
      antialias: true
    }});

    map.on('load', () => {{
      map.addSource('buildings', {{ type: 'geojson', data: geojson }});
      map.addLayer({{
        id: '3d-buildings',
        type: 'fill-extrusion',
        source: 'buildings',
        paint: {{
          'fill-extrusion-color': ['interpolate', ['linear'], ['get', '{height_col}'], 0, '#f2f0f7', 10, '#cbc9e2', 30, '#9e9ac8', 60, '#6a51a3'],
          'fill-extrusion-height': ['get', '{height_col}'],
          'fill-extrusion-base': 0,
          'fill-extrusion-opacity': 0.9
        }}
      }});

      info.innerHTML += '<br>Rendered features: ' + geojson.features.length;
    }});

    map.on('error', (e) => {{
      console.error('Map error:', e.error || e);
      document.getElementById('info').innerHTML += '<br><strong>Map error:</strong> ' + (e.error && e.error.message ? e.error.message : JSON.stringify(e));
    }});

  }} catch (err) {{
    console.error('Rendering failed', err);
    document.body.innerHTML = '<pre style="color:red">Rendering failed: ' + err + '</pre>' + document.body.innerHTML;
  }}
}})();
</script>
</body>
</html>
"""
out = Path('buildings_3d_sample.html')
out.write_text(html, encoding='utf-8')
print('Saved sample HTML to', out.resolve())

