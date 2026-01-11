"""
Data Acquisition Module
Fetches building footprints, from pdok using WFS services 

"""
from shapely.geometry import box
import requests
import geopandas as gpd
from typing import Dict, List, Optional, Tuple, Union
import json
import numpy as np
import time
from pathlib import Path

#============================================================
# 1. Fetch Building Footprints from PDOK BAG3D WFS
#============================================================

def fetch_pdok_buildings(
    area: Union[
        Tuple[float, float, float, float],  # bbox (WGS84)
        str,                                 # geojson / shp
        gpd.GeoDataFrame,
        gpd.GeoSeries
    ],
    output_path: Optional[str] = "buildings.geojson",
    page_size: int = 1000,
) -> gpd.GeoDataFrame:
    """
    Fetch BAG3D LoD1.2 buildings intersecting `area` using the WFS API.

    This implementation uses the WFS bbox parameter + paging (count/startIndex)
    to fetch *all* features that intersect the study area. Results are fetched
    in the BAG3D native CRS (EPSG:28992) and clipped to the exact area.
    """

   
    # Normalise study area : if the input was 

    if isinstance(area, tuple):
        area_gdf = gpd.GeoDataFrame(geometry=[box(*area)], crs="EPSG:4326")
    elif isinstance(area, (str, Path)):
        area_gdf = gpd.read_file(area)
    elif isinstance(area, (gpd.GeoDataFrame, gpd.GeoSeries)):
        area_gdf = gpd.GeoDataFrame(geometry=area.geometry)
    else:
        raise TypeError("Unsupported area input type")

    # target CRS for BAG3D WFS is EPSG:28992
    area_proj = area_gdf.to_crs("EPSG:28992")
    minx, miny, maxx, maxy = area_proj.total_bounds

    
    # Page through WFS using bbox :
   
    url = "https://data.3dbag.nl/api/BAG3D/wfs"
    params_base = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": "BAG3D:lod12",
        "outputFormat": "json",
        "srsName": "EPSG:28992",
    }

    features = []
    start_index = 0

    while True:
        params = params_base.copy()
        params.update({
            "bbox": f"{minx},{miny},{maxx},{maxy}",
            "count": page_size,
            "startIndex": start_index,
        })

        r = requests.get(url, params=params)
        r.raise_for_status()

        data = r.json()
        batch = data.get("features", [])
        if not batch:
            break

        features.extend(batch)
        batch_len = len(batch)
        start_index += batch_len

        # if server returned fewer than requested, we've reached the end
        if batch_len < page_size:
            break

    # -----------------------------
    # Build GeoDataFrame and clip to exact area
    # -----------------------------
    if not features:
        buildings = gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs="EPSG:28992")
    else:
        buildings = gpd.GeoDataFrame.from_features(features)
        buildings = buildings.set_crs("EPSG:28992", allow_override=True)
        buildings = gpd.clip(buildings, area_proj)

    # Save to file if output_path is given
    if output_path:
        buildings.to_file(output_path, driver="GeoJSON")

    return buildings



#==============================================================
# 2. Fetch Solar PV Energy Data from PVGIS PVcalc API
#==============================================================

class PVGISPVCalcClient:
    """
      PV Energy = Radiation × Panel Physics × System Assumptions

   fetch Solar PV engery data from number of inputs (cordinates ,  bounding box)
    """

    BASE_URL = "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc"

    def __init__(self, peakpower=1, loss=14, timeout=30):
        self.peakpower = peakpower
        self.loss = loss
        self.timeout = timeout

    def _fetch_point(self, lat, lon):
        """
        Internal method: fetch PVGIS data for a single point.
        """
        params = {
            "lat": lat,
            "lon": lon,
            "peakpower": self.peakpower,
            "loss": self.loss,
            "outputformat": "json",
        }

        r = requests.get(self.BASE_URL, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def fetch_bbox_geojson(self, bbox, step_km=1.0, sleep=0.05):
        """
        Fetch PVGIS PVcalc results for a bounding box
        and return a GeoJSON FeatureCollection.

        bbox = (min_lon, min_lat, max_lon, max_lat)
        """

        min_lon, min_lat, max_lon, max_lat = bbox
        step_deg = step_km / 111.0  # km → degrees (approx)

        features = []
        feature_id = 1

        lats = np.arange(min_lat, max_lat, step_deg)
        lons = np.arange(min_lon, max_lon, step_deg)

        for lat in lats:
            for lon in lons:
                data = self._fetch_point(lat, lon)

                feature = {
                    "type": "Feature",
                    "id": feature_id,
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    },
                    "properties": {
                        "E_y": data["outputs"]["totals"]["fixed"]["E_y"],
                        "loss": self.loss,
                        "source": "PVGIS PVcalc"
                    }
                }

                features.append(feature)
                feature_id += 1
                time.sleep(sleep)

        return {
            "type": "FeatureCollection",
            "features": features
        }

    def save_geojson(self, geojson, filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(geojson, f, indent=2)


if __name__ == "__main__":
    # =============================================================================
    # FULL AMSTERDAM DATA (Run once to fetch complete dataset)
    # Uncomment the block below to fetch full Amsterdam data
    # =============================================================================
    """
    print("=" * 60)
    print("FETCHING FULL AMSTERDAM DATA (This will take about 22 minutes)")
    print("=" * 60)
    
    amsterdam_full = (4.728, 52.278, 5.079, 52.431)  # ~35km × ~17km (full Amsterdam)
    
    # Fetch full building footprints
    buildings_full = fetch_pdok_buildings(amsterdam_full, output_path="data/footprints.json")
    print(f"✓ Saved {len(buildings_full)} buildings to data/footprints.json")
    
    # Fetch full solar data
    client = PVGISPVCalcClient()
    geojson_full = client.fetch_bbox_geojson(
        bbox=amsterdam_full,
        step_km=1.0,  # 1km grid spacing
        sleep=0.01
    )
    client.save_geojson(geojson_full, "data/solar.json")
    print(f"✓ Saved {len(geojson_full['features'])} solar points to data/solar.json")
    """
    
    # =============================================================================
    # TEST DATA (Smaller area for development and testing)
    # This runs by default for quick iterations
    # =============================================================================
    print("=" * 60)
    print("FETCHING TEST DATA (Small area for quick testing)")
    print("=" * 60)
    
    amsterdam_test = (4.88, 52.36, 4.92, 52.38)  # ~3km × ~2km (Central Amsterdam)
    
    # Fetch test building footprints
    buildings_test = fetch_pdok_buildings(amsterdam_test, output_path="data/test_footprints.json")
    print(f"✓ Saved {len(buildings_test)} buildings to data/test_footprints.json")
    
    # Fetch test solar data
    client = PVGISPVCalcClient()
    geojson_test = client.fetch_bbox_geojson(
        bbox=amsterdam_test,
        step_km=1.0,  # 1km grid spacing
        sleep=0.01
    )
    client.save_geojson(geojson_test, "data/test_solar.json")
    print(f"✓ Saved {len(geojson_test['features'])} solar points to data/test_solar.json")
    print("\n✓ Test data ready! Use test_footprints.json and test_solar.json for development.")

