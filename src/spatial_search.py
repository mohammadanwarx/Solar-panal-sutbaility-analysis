"""
Spatial Search Modules
this module's searching function to manipulate and retrieve solar suitability. 

1- SpatialIndex: uses Kd-tree algorithms to retrieve buildings using this functionality 
  -find_nearest_neighbors
  -find_within_radius
  
  2- other searching functions
   - binary_search_building_by_score
   - find_top_k_buildings

"""
from src.data_acquisition import fetch_pdok_buildings
import numpy as np
import pandas as pd 
import geopandas as gpd
from shapely.geometry import Point, Polygon
from typing import List, Tuple, Optional
from scipy.spatial import KDTree
from scipy.spatial import ckdtree



#=======================================
# spatial index module
class SpatialIndex:
    """
    Spatial index using KD-tree for efficient spatial queries.
    
    The KD-tree algorithm organizes points in k-dimensional space (2D for geographic coordinates)
    for efficient nearest neighbor and range searches.
    
    Time Complexity:
    - Construction: O(n log n)
    - Query: O(log n) average case
    """
    
    def __init__(self, buildings_gdf: gpd.GeoDataFrame):
        """
        Initialize spatial index with building centroids.
        
        Parameters
        ----------
        buildings_gdf : gpd.GeoDataFrame
            GeoDataFrame containing building geometries
        """
        self.buildings_gdf = buildings_gdf.copy()
        
        # Extract centroids for KD-tree
        self.buildings_gdf['centroid'] = self.buildings_gdf.geometry.centroid
        self.buildings_gdf['x'] = self.buildings_gdf.centroid.x
        self.buildings_gdf['y'] = self.buildings_gdf.centroid.y
        
         # Build KD-tree from centroids
        x = self.buildings_gdf['x'].to_numpy(dtype=float)
        y = self.buildings_gdf['y'].to_numpy(dtype=float)
        self.coordinates = np.column_stack((x, y))
        
        self.kdtree = KDTree(self.coordinates)
        
        

        
    def find_nearest_neighbors(
        self,
        point: Point,
        k: int = 5
    ) -> gpd.GeoDataFrame:
        """
        Find kd nearest buildings to a given point using KD-tree.
        
        Algorithm: KD-tree nearest neighbor search
        Time Complexity: O(log n) average case
        
        Parameters
        ----------       
        point : Point
            Query point
        k : int
            Number of nearest neighbors to find
        
        Returns
        -------
        gpd.GeoDataFrame
            k nearest buildings sorted by distance
        """
        
        query_point = np.array([point.x, point.y])
        
        # KD-tree query: finds k nearest neighbors
        distances, indices = self.kdtree.query(query_point, k=k)
        
        # Return corresponding buildings
        nearest_buildings = self.buildings_gdf.iloc[indices].copy()
        nearest_buildings['distance'] = distances
        
        return nearest_buildings
    
    def find_within_radius(
        self,
        point: Point,
        radius: float
    ) -> gpd.GeoDataFrame:
        """
        Find all buildings within a given radius using KD-tree range query.
        
        Algorithm: KD-tree range search
        Time Complexity: O(log n + m) where m is number of results
        
        Parameters
        ----------
        point : Point
            Query point (building centroid)
        radius : float
            Search radius in coordinate units (meters for projected CRS)
        
        Returns
        -------
        gpd.GeoDataFrame
            Buildings within radius
        """
        query_point = np.array([point.x, point.y])
        
        # KD-tree range query: finds all points within radius
        indices = self.kdtree.query_ball_point(query_point, radius)
        result = self.buildings_gdf.iloc[indices].copy()
        if result.empty:
           print("No buildings found within radius.")
        return result


        
        # Return buildings within radius
        nearby_buildings = self.buildings_gdf.iloc[indices].copy()
        
        # Calculate actual distances
        nearby_buildings['distance'] = nearby_buildings.apply(
            lambda row: point.distance(row.centroid),
            axis=1
        )
        return nearby_buildings.sort_values('distance')


def binary_search_building_by_score(
    buildings_gdf: gpd.GeoDataFrame,
    target_score: float,
    score_column: str = "suitability_score"
) -> gpd.GeoDataFrame:
    """
    return geo dataframe

    Requires: buildings_gdf must contain score_column.

    Parameters
    ---------
    buildings_gdf: gpd.GeoDataFrame
      buildings to search 

    target_score: float
      Any : float represent the target score to be searched 

    score_column: str
      a sutability score colunm in the gpd.GeoDataFrame
    """
    if buildings_gdf.empty:
        # return an empty GeoDataFrame with the same schema
        return buildings_gdf.iloc[0:0].copy()

    # Ensure sorted input for binary search
    gdf = buildings_gdf.sort_values(score_column).reset_index(drop=True)
    scores = gdf[score_column].values

    left, right = 0, len(scores) - 1
    closest_idx = 0
    min_diff = float("inf")

    while left <= right:
        mid = (left + right) // 2
        diff = abs(scores[mid] - target_score)

        if diff < min_diff:
            min_diff = diff
            closest_idx = mid

        if scores[mid] < target_score:
            left = mid + 1
        elif scores[mid] > target_score:
            right = mid - 1
        else:
            break  # exact match
    
    return gdf.iloc[[closest_idx]]


   
def find_top_k_buildings(
    buildings_gdf: gpd.GeoDataFrame,
    k: int,
    score_column: str = 'suitability_score'
) -> gpd.GeoDataFrame:
    """
    Find top k buildings using heap-based selection (via pandas).
    
    Algorithm: Heap-based partial sort (nth-element)
    Time Complexity: O(n log k)
    Space Complexity: O(k)
    
    More efficient than full sort when k << n.
    
    Parameters
    ----------
    buildings_gdf : gpd.GeoDataFrame
        Buildings to search
    k : int
        Number of top buildings to return
    score_column : str
        Column to rank by
    
    Returns
    -------
    gpd.GeoDataFrame
        Top k buildings by score
    """
    if buildings_gdf.empty or k <= 0:
        return buildings_gdf.iloc[0:0].copy()

    if score_column not in buildings_gdf.columns:
        raise KeyError(f"Column '{score_column}' not found")

    return buildings_gdf.nlargest(k, score_column)


