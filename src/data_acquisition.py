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

    # ----------------------------------------
    # 3. Build GeoDataFrame and clip to exact area
   
    if not features:
        buildings = gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs="EPSG:28992")
    else:
        buildings = gpd.GeoDataFrame.from_features(features)
        buildings = buildings.set_crs("EPSG:28992", allow_override=True)
        buildings = gpd.clip(buildings, area_proj)

    # 4. Save (its optinal)
    if output_path:
        buildings.to_file(output_path, driver="GeoJSON")

    return buildings

#==============================================================

# solar 
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
