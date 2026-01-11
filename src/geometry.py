"""
Geometry Module
Calculates roof area, orientation, and slope from building footprints.
Interpolates solar values for buildings from point data.
"""

import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, Point
from typing import Tuple, Optional, Dict
import json
from pathlib import Path
from scipy.interpolate import griddata


def calculate_roof_area(geometry: Polygon) -> float:
    """
    Calculate roof area from building footprint geometry.
    
    Parameters
    ----------
    geometry : Polygon
        Building footprint geometry
    
    Returns
    -------
    float
        Roof area in square meters
    """
    return geometry.area


def calculate_roof_orientation(geometry: Polygon) -> float:
    """
    Calculate roof orientation (aspect/azimuth) based on longest edge.
    
    Parameters
    ----------
    geometry : Polygon
        Building footprint geometry
    
    Returns
    -------
    float
        Orientation in degrees (0-360), where 0=North, 90=East, 180=South, 270=West
    """
    # Failed yesterday because some buildings are MultiPolygons
    if geometry.geom_type == 'MultiPolygon':
        # Get the largest polygon by area
        geometry = max(geometry.geoms, key=lambda p: p.area)
    
    coords = list(geometry.exterior.coords)[:-1]  # Exclude duplicate last point
    
    # Find longest edge
    max_length = 0
    longest_edge = None
    
    for i in range(len(coords)):
        p1 = np.array(coords[i])
        p2 = np.array(coords[(i + 1) % len(coords)])
        
        length = np.linalg.norm(p2 - p1)
        if length > max_length:
            max_length = length
            longest_edge = (p1, p2)
    
    if longest_edge is None:
        return 0.0
    
    # Calculate angle of longest edge
    p1, p2 = longest_edge
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    
    # Convert to azimuth (0=North, clockwise)
    angle_rad = np.arctan2(dx, dy)
    angle_deg = np.degrees(angle_rad)
    
    # Normalize to 0-360
    azimuth = (angle_deg + 360) % 360
    
    return azimuth


def calculate_roof_slope(building_height: float, roof_type: str = "flat") -> float:
    """
    Calculate roof slope angle.
    
    Parameters
    ----------
    building_height : float
        Building height in meters
    roof_type : str
        Type of roof: 'flat', 'pitched', 'gabled'
    
    Returns
    -------
    float
        Slope angle in degrees
    """
    # Default slope values based on roof type
    slope_defaults = {
        "flat": 2.0,      # Slight slope for drainage
        "pitched": 25.0,  # Typical pitched roof
        "gabled": 30.0    # Steeper gabled roof
    }
    
    return slope_defaults.get(roof_type.lower(), 2.0)


def get_roof_vertices(geometry: Polygon) -> np.ndarray:
    """
    Extract vertices coordinates from roof geometry.
    
    Parameters
    ----------
    geometry : Polygon
        Roof geometry
    
    Returns
    -------
    np.ndarray
        Array of vertex coordinates
    """
    # Handle MultiPolygon by using the largest polygon
    if geometry.geom_type == 'MultiPolygon':
        # Get the largest polygon by area
        geometry = max(geometry.geoms, key=lambda p: p.area)
    
    return np.array(geometry.exterior.coords)


# ============================================================================
# Functional approach: Solar interpolation functions
# ============================================================================

def load_solar_data(filepath: str = "data/solar.json") -> Tuple[np.ndarray, np.ndarray]:
    """
    Load solar point data from JSON file.
    
    Parameters
    ----------
    filepath : str
        Path to solar data JSON file
    
    Returns
    -------
    Tuple[np.ndarray, np.ndarray]
        Coordinates (N, 2) and solar energy values (N,)
    """
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    coords = []
    values = []
    
    for feature in data['features']:
        lon, lat = feature['geometry']['coordinates']
        e_y = feature['properties']['E_y']
        coords.append([lon, lat])
        values.append(e_y)
    
    return np.array(coords), np.array(values)


def interpolate_solar_at_point(point: Point, solar_coords: np.ndarray, 
                                solar_values: np.ndarray, method: str = 'linear') -> float:
    """
    Interpolate solar energy value at a specific point.
    
    Parameters
    ----------
    point : Point
        Location to interpolate at
    solar_coords : np.ndarray
        Array of solar point coordinates (N, 2)
    solar_values : np.ndarray
        Array of solar energy values (N,)
    method : str
        Interpolation method: 'linear', 'nearest', or 'cubic'
    
    Returns
    -------
    float
        Interpolated solar energy value (kWh/year)
    """
    query_point = np.array([[point.x, point.y]])
    
    try:
        interpolated = griddata(
            solar_coords, 
            solar_values, 
            query_point, 
            method=method
        )[0]
        
        # If interpolation fails (outside convex hull), use nearest neighbor
        if np.isnan(interpolated):
            interpolated = griddata(
                solar_coords, 
                solar_values, 
                query_point, 
                method='nearest'
            )[0]
        
        return float(interpolated)
    except Exception:
        # Fallback to nearest neighbor
        distances = np.linalg.norm(solar_coords - query_point, axis=1)
        nearest_idx = np.argmin(distances)
        return float(solar_values[nearest_idx])


# ============================================================================
# OOP approach: Building geometry processor
# ============================================================================

class BuildingGeometryProcessor:
    """
    Object-oriented processor for building geometry analysis and solar interpolation.
    
    Attributes
    ----------
    buildings_gdf : gpd.GeoDataFrame
        GeoDataFrame containing building footprints
    solar_coords : np.ndarray
        Coordinates of solar data points
    solar_values : np.ndarray
        Solar energy values at each point
    """
    
    def __init__(self, buildings_path: str = "data/footprints.json", 
                 solar_path: str = "data/solar.json"):
        """
        Initialize the processor with building and solar data.
        
        Parameters
        ----------
        buildings_path : str
            Path to building footprints GeoJSON
        solar_path : str
            Path to solar data JSON
        """
        self.buildings_path = buildings_path
        self.solar_path = solar_path
        self.buildings_gdf = None
        self.solar_coords = None
        self.solar_values = None
        
        self._load_data()
    
    def _load_data(self):
        """Load building and solar data from files."""
        # Load buildings
        if Path(self.buildings_path).exists():
            self.buildings_gdf = gpd.read_file(self.buildings_path)
            print(f"Loaded {len(self.buildings_gdf)} buildings from {self.buildings_path}")
        else:
            print(f"Warning: {self.buildings_path} not found")
            self.buildings_gdf = gpd.GeoDataFrame()
        
        # Load solar data
        if Path(self.solar_path).exists():
            self.solar_coords, self.solar_values = load_solar_data(self.solar_path)
            print(f"Loaded {len(self.solar_values)} solar data points from {self.solar_path}")
        else:
            print(f"Warning: {self.solar_path} not found")
            self.solar_coords = np.array([])
            self.solar_values = np.array([])
    
    def compute_roof_properties(self) -> gpd.GeoDataFrame:
        """
        Compute roof area, orientation, and vertices for all buildings.
        
        Returns
        -------
        gpd.GeoDataFrame
            Buildings with added roof property columns
        """
        if self.buildings_gdf.empty:
            print("No buildings loaded")
            return self.buildings_gdf
        
        print("Computing roof properties...")
        
        # Calculate roof area
        self.buildings_gdf['roof_area_m2'] = self.buildings_gdf.geometry.apply(
            calculate_roof_area
        )
        
        # Calculate roof orientation
        self.buildings_gdf['roof_orientation_deg'] = self.buildings_gdf.geometry.apply(
            calculate_roof_orientation
        )
        
        # Get number of vertices
        self.buildings_gdf['num_vertices'] = self.buildings_gdf.geometry.apply(
            lambda geom: len(get_roof_vertices(geom)) - 1
        )
        
        # Extract height if available
        if 'h_dak_max' in self.buildings_gdf.columns:
            self.buildings_gdf['building_height_m'] = self.buildings_gdf['h_dak_max']
        
        print(f"✓ Computed properties for {len(self.buildings_gdf)} buildings")
        return self.buildings_gdf
    
    def interpolate_solar_values(self, method: str = 'linear') -> gpd.GeoDataFrame:
        """
        Interpolate solar energy values for all buildings using their centroids.
        
        Parameters
        ----------
        method : str
            Interpolation method: 'linear', 'nearest', or 'cubic'
        
        Returns
        -------
        gpd.GeoDataFrame
            Buildings with added solar energy column
        """
        if self.buildings_gdf.empty or len(self.solar_values) == 0:
            print("No buildings or solar data loaded")
            return self.buildings_gdf
        
        print(f"Interpolating solar values using {method} method...")
        
        # Get building centroids
        centroids = self.buildings_gdf.geometry.centroid
        
        # Interpolate for each building
        solar_values = []
        for centroid in centroids:
            value = interpolate_solar_at_point(
                centroid, 
                self.solar_coords, 
                self.solar_values, 
                method
            )
            solar_values.append(value)
        
        self.buildings_gdf['solar_energy_kwh_year'] = solar_values
        
        # Convert E_y (kWh/year per kWp) to solar irradiance (kWh/m²/year)
        # E_y is energy from 1kWp system. Standard test conditions: 1kWp = 1000W/m² 
        # Typical panel efficiency is 18%, so 1kWp needs ~5.56 m² of panels
        # Therefore: irradiance ≈ E_y / 5.56 * efficiency_factor
        # Simplified: irradiance ≈ E_y (since E_y already accounts for typical conditions)
        self.buildings_gdf['solar_irradiance'] = solar_values
        
        print(f"✓ Interpolated solar values for {len(self.buildings_gdf)} buildings")
        print(f"  Mean solar energy: {np.mean(solar_values):.1f} kWh/year")
        print(f"  Range: {np.min(solar_values):.1f} - {np.max(solar_values):.1f} kWh/year")
        
        return self.buildings_gdf
    
    def process_all(self, output_path: Optional[str] = None) -> gpd.GeoDataFrame:
        """
        Run complete processing pipeline: compute roof properties and interpolate solar values.
        
        Parameters
        ----------
        output_path : str, optional
            Path to save processed buildings GeoJSON
        
        Returns
        -------
        gpd.GeoDataFrame
            Fully processed buildings with all computed properties
        """
        print("=" * 70)
        print("BUILDING GEOMETRY PROCESSING PIPELINE")
        print("=" * 70)
        
        # Compute roof properties
        self.compute_roof_properties()
        
        # Interpolate solar values
        self.interpolate_solar_values()
        
        # Save if output path provided
        if output_path:
            self.buildings_gdf.to_file(output_path, driver="GeoJSON")
            print(f"✓ Saved processed buildings to {output_path}")
        
        print("=" * 70)
        print("PROCESSING COMPLETE")
        print("=" * 70)
        
        return self.buildings_gdf
    
    def get_summary_statistics(self) -> Dict:
        """
        Get summary statistics of processed buildings.
        
        Returns
        -------
        Dict
            Dictionary containing summary statistics
        """
        if self.buildings_gdf.empty:
            return {}
        
        stats = {
            'num_buildings': len(self.buildings_gdf),
            'total_roof_area_m2': self.buildings_gdf['roof_area_m2'].sum() if 'roof_area_m2' in self.buildings_gdf.columns else 0,
            'avg_roof_area_m2': self.buildings_gdf['roof_area_m2'].mean() if 'roof_area_m2' in self.buildings_gdf.columns else 0,
            'avg_solar_energy_kwh': self.buildings_gdf['solar_energy_kwh_year'].mean() if 'solar_energy_kwh_year' in self.buildings_gdf.columns else 0,
            'total_solar_potential_kwh': self.buildings_gdf['solar_energy_kwh_year'].sum() if 'solar_energy_kwh_year' in self.buildings_gdf.columns else 0,
        }
        
        return stats


# ============================================================================
# Main execution
# ============================================================================

if __name__ == "__main__":
    # =============================================================================
    # FULL AMSTERDAM DATA (Run once to process complete dataset)
    # Uncomment the block below to process full Amsterdam data
    # This will take significant time (~30-60 minutes for full dataset)
    # =============================================================================
    """
    print("=" * 70)
    print("PROCESSING FULL AMSTERDAM DATA")
    print("=" * 70)
    
    processor = BuildingGeometryProcessor(
        buildings_path="data/footprints.json",
        solar_path="data/solar.json"
    )
    
    # Process all buildings
    processed_buildings = processor.process_all(
        output_path="data/processed_buildings.json"
    )
    
    # Get summary statistics
    stats = processor.get_summary_statistics()
    print("\nSummary Statistics:")
    print(f"  Total buildings: {stats['num_buildings']}")
    print(f"  Total roof area: {stats['total_roof_area_m2']:,.0f} m²")
    print(f"  Average roof area: {stats['avg_roof_area_m2']:.1f} m²")
    print(f"  Average solar energy: {stats['avg_solar_energy_kwh']:.1f} kWh/year")
    print(f"  Total solar potential: {stats['total_solar_potential_kwh']:,.0f} kWh/year")
    
    print("\n✓ Full data processed! Output saved to data/processed_buildings.json")
    print("  This file can be downloaded directly from the repository.")
    """
    
    # =============================================================================
    # TEST DATA (Smaller subset for development and testing)
    # This runs by default for quick iterations
    # =============================================================================
    print("=" * 70)
    print("PROCESSING TEST DATA (Small area for quick testing)")
    print("=" * 70)
    
    processor = BuildingGeometryProcessor(
        buildings_path="data/test_footprints.json",
        solar_path="data/test_solar.json"
    )
    
    # Process all buildings
    processed_buildings = processor.process_all(
        output_path="data/processed_test_buildings.json"
    )
    
    # Get summary statistics
    stats = processor.get_summary_statistics()
    print("\nSummary Statistics:")
    print(f"  Total buildings: {stats['num_buildings']}")
    print(f"  Total roof area: {stats['total_roof_area_m2']:,.0f} m²")
    print(f"  Average roof area: {stats['avg_roof_area_m2']:.1f} m²")
    print(f"  Average solar energy: {stats['avg_solar_energy_kwh']:.1f} kWh/year")
    print(f"  Total solar potential: {stats['total_solar_potential_kwh']:,.0f} kWh/year")
    
    print("\n✓ Test data processed! Use processed_test_buildings.json for development.")
