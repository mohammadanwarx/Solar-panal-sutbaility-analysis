"""
Utility Module
Helper functions for data validation, coordinate transformations, and file I/O.
"""

import geopandas as gpd
import json
from pathlib import Path
from typing import Union, Dict, Any
import logging


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Setup logging configuration.
    
    Parameters
    ----------
    log_level : str
        Logging level (DEBUG, INFO, WARNING, ERROR)
    
    Returns
    -------
    logging.Logger
        Configured logger
    """
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def validate_geometry(geometry) -> bool:
    """
    Check if geometry is valid.
    
    Parameters
    ----------
    geometry : shapely.geometry
        Geometry to validate
    
    Returns
    -------
    bool
        True if valid, False otherwise
    """
    return geometry is not None and geometry.is_valid


def transform_crs(
    gdf: gpd.GeoDataFrame,
    target_crs: Union[str, int]
) -> gpd.GeoDataFrame:
    """
    Transform GeoDataFrame to target coordinate reference system.
    
    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        Input GeoDataFrame
    target_crs : str or int
        Target CRS (e.g., 'EPSG:4326' or 4326)
    
    Returns
    -------
    gpd.GeoDataFrame
        Transformed GeoDataFrame
    """
    if isinstance(target_crs, int):
        target_crs = f"EPSG:{target_crs}"
    
    return gdf.to_crs(target_crs)


def save_geojson(gdf: gpd.GeoDataFrame, filepath: Union[str, Path]) -> None:
    """
    Save GeoDataFrame to GeoJSON file.
    
    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        GeoDataFrame to save
    filepath : str or Path
        Output file path
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(filepath, driver='GeoJSON')


def load_geojson(filepath: Union[str, Path]) -> gpd.GeoDataFrame:
    """
    Load GeoJSON file into GeoDataFrame.
    
    Parameters
    ----------
    filepath : str or Path
        Input file path
    
    Returns
    -------
    gpd.GeoDataFrame
        Loaded GeoDataFrame
    """
    return gpd.read_file(filepath)


def load_config(config_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load configuration from JSON file.
    
    Parameters
    ----------
    config_path : str or Path
        Path to config file
    
    Returns
    -------
    dict
        Configuration dictionary
    """
    with open(config_path, 'r') as f:
        return json.load(f)


def format_area(area_m2: float, unit: str = "m2") -> str:
    """
    Format area with appropriate units.
    
    Parameters
    ----------
    area_m2 : float
        Area in square meters
    unit : str
        Target unit ('m2', 'ha', 'acres')
    
    Returns
    -------
    str
        Formatted area string
    """
    if unit == "m2":
        return f"{area_m2:.2f} m²"
    elif unit == "ha":
        return f"{area_m2 / 10000:.2f} ha"
    elif unit == "acres":
        return f"{area_m2 / 4046.86:.2f} acres"
    else:
        raise ValueError(f"Unknown unit: {unit}")


def format_energy(energy_kwh: float, unit: str = "kwh") -> str:
    """
    Format energy with appropriate units.
    
    Parameters
    ----------
    energy_kwh : float
        Energy in kWh
    unit : str
        Target unit ('kwh', 'mwh')
    
    Returns
    -------
    str
        Formatted energy string
    """
    if unit == "kwh":
        return f"{energy_kwh:.2f} kWh"
    elif unit == "mwh":
        return f"{energy_kwh / 1000:.2f} MWh"
    else:
        raise ValueError(f"Unknown unit: {unit}")
