"""
Visualization Module for Solar Panel Suitability Mapping

This module provides functions for creating visualizations including:
- Suitability maps
- Statistical charts and figures
- Reports and summaries
"""

import os
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap, Normalize
import seaborn as sns
from shapely.geometry import box

# Optional imports for interactive maps
try:
    import folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
    print("Warning: folium not installed. Interactive maps will not be available.")


# ============================================================================
# Configuration
# ============================================================================

# Default output directories
FIGURES_DIR = Path("outputs/figures")
MAPS_DIR = Path("outputs/maps")
REPORTS_DIR = Path("outputs/reports")

# Ensure output directories exist
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
MAPS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Visualization styling
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10


# ============================================================================
# Map Generation Functions
# ============================================================================

def plot_solar_potential_choropleth(
    buildings_gdf: gpd.GeoDataFrame,
    column: str = 'solar_potential_kwh',
    output_path: Optional[str] = None,
    title: str = 'Building-level Solar Potential',
    cmap: str = 'autumn',
    figsize: Tuple[int, int] = (12, 10),
    dark_theme: bool = True
) -> None:
    """
    Create a choropleth map showing solar potential with enhanced styling.
    
    Parameters
    ----------
    buildings_gdf : gpd.GeoDataFrame
        GeoDataFrame with building geometries and solar data
    column : str
        Column name for solar potential values
    output_path : str, optional
        Path to save the figure
    title : str
        Map title
    cmap : str
        Matplotlib colormap name
    figsize : tuple
        Figure size (width, height)
    dark_theme : bool
        Use dark background theme
    """
    if output_path is None:
        output_path = str(MAPS_DIR / "solar_potential_choropleth.png")
    
    # Clean data
    solar_data = buildings_gdf[[column, 'geometry']].copy()
    solar_data = solar_data.dropna(subset=[column])
    solar_data = solar_data[solar_data[column] > 0]
    
    if solar_data.empty:
        print(f"No valid data in column '{column}'")
        return
    
    # Compute percentile limits to handle outliers
    vmin = solar_data[column].quantile(0.02)
    vmax = solar_data[column].quantile(0.98)
    
    # Create normalization
    norm = Normalize(vmin=vmin, vmax=vmax, clip=True)
    
    # Create figure with styling
    bg_color = '#1a1a1a' if dark_theme else 'white'
    text_color = 'white' if dark_theme else 'black'
    axis_bg = '#0d0d0d' if dark_theme else '#f0f0f0'
    
    fig, ax = plt.subplots(figsize=figsize, facecolor=bg_color)
    
    # Plot choropleth
    solar_data.plot(
        column=column,
        cmap=cmap,
        linewidth=0,
        ax=ax,
        legend=True,
        norm=norm,
        legend_kwds={
            "label": f"{column.replace('_', ' ').title()} (2–98 percentile)",
            "shrink": 0.6,
            "pad": 0.05
        }
    )
    
    ax.set_facecolor(axis_bg)
    ax.set_title(title, fontsize=16, fontweight='bold', color=text_color, pad=20)
    ax.set_axis_off()
    
    # Style colorbar
    if len(ax.get_figure().get_axes()) > 1:
        cbar = ax.get_figure().get_axes()[1]
        cbar.tick_params(colors=text_color, labelsize=10)
        cbar.yaxis.label.set_color(text_color)
        cbar.yaxis.label.set_fontsize(11)
        cbar.yaxis.label.set_fontweight('bold')
    
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', facecolor=bg_color)
    plt.close()
    
    print(f"Solar potential choropleth saved to: {output_path}")


def create_interactive_folium_map(
    buildings_gdf: gpd.GeoDataFrame,
    column: str = 'solar_potential_kwh',
    output_path: Optional[str] = None,
    zoom_start: int = 15,
    tiles: str = 'Esri.WorldImagery',
    bbox: Optional[Tuple[float, float, float, float]] = None,
    max_features: int = 5000
) -> Optional[object]:
    """
    Create an interactive Folium map with color-coded buildings.
    
    Parameters
    ----------
    buildings_gdf : gpd.GeoDataFrame
        GeoDataFrame with building geometries
    column : str
        Column to use for color coding
    output_path : str, optional
        Path to save HTML file
    zoom_start : int
        Initial zoom level
    tiles : str
        Map tile provider
    bbox : tuple, optional
        Bounding box (min_lon, min_lat, max_lon, max_lat) to clip data
    max_features : int
        Maximum number of features to render (for performance)
    
    Returns
    -------
    folium.Map or None
        Folium map object if folium is available
    """
    if not FOLIUM_AVAILABLE:
        print("Error: folium not installed. Install with: pip install folium")
        return None
    
    if output_path is None:
        output_path = str(MAPS_DIR / "interactive_map.html")
    
    # Clip to bbox if provided
    if bbox is not None:
        aoi_box = box(*bbox)
        aoi_gdf = gpd.GeoDataFrame(geometry=[aoi_box], crs="EPSG:4326")
        buildings_clipped = buildings_gdf.to_crs("EPSG:4326")
        buildings_clipped = gpd.clip(buildings_clipped, aoi_gdf)
        print(f"Clipped to {len(buildings_clipped)} buildings in bbox")
    else:
        buildings_clipped = buildings_gdf.copy()
    
    # Convert to WGS84 if needed
    if buildings_clipped.crs != 'EPSG:4326':
        buildings_clipped = buildings_clipped.to_crs('EPSG:4326')
    
    # Filter valid data
    buildings_for_map = buildings_clipped[
        (buildings_clipped[column].notna()) & 
        (buildings_clipped[column] > 0)
    ].copy()
    
    if buildings_for_map.empty:
        print(f"No valid data in column '{column}'")
        return None
    
    # Limit features for performance
    if len(buildings_for_map) > max_features:
        print(f"⚠️  Dataset has {len(buildings_for_map)} buildings. Sampling top {max_features} by {column} for performance.")
        buildings_for_map = buildings_for_map.nlargest(max_features, column)
    
    # Get map center using bounds (better for geographic coordinates)
    bounds = buildings_for_map.total_bounds  # [minx, miny, maxx, maxy]
    center_lon = (bounds[0] + bounds[2]) / 2
    center_lat = (bounds[1] + bounds[3]) / 2
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        tiles=tiles
    )
    
    # Use Choropleth for efficient rendering
    try:
        # Convert to JSON for folium
        buildings_json = buildings_for_map[[column, 'geometry']].to_json()
        
        folium.Choropleth(
            geo_data=buildings_json,
            data=buildings_for_map,
            columns=[buildings_for_map.index, column],
            key_on='feature.id',
            fill_color='YlOrRd',
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name=column.replace('_', ' ').title()
        ).add_to(m)
        
        print(f"✓ Rendered {len(buildings_for_map)} buildings efficiently using Choropleth")
    except Exception as e:
        print(f"Warning: Choropleth failed ({e}), falling back to GeoJson...")
        # Fallback: add as single GeoJson layer (still much faster than loop)
        folium.GeoJson(
            buildings_for_map[[column, 'geometry']],
            style_function=lambda x: {
                'fillColor': '#FF6347',
                'color': '#8B0000',
                'weight': 1,
                'fillOpacity': 0.7
            }
        ).add_to(m)
    
    # Save map
    m.save(output_path)
    print(f"Interactive map saved to: {output_path}")
    
    return m


def plot_pairwise_analysis(
    buildings_gdf: gpd.GeoDataFrame,
    column: str = 'solar_potential_kwh',
    output_path: Optional[str] = None,
    hue_column: Optional[str] = None
) -> None:
    """
    Create pairwise analysis plots using seaborn.
    
    Parameters
    ----------
    buildings_gdf : gpd.GeoDataFrame
        GeoDataFrame with building data
    column : str
        Primary column for analysis
    output_path : str, optional
        Path to save figure
    hue_column : str, optional
        Column to use for color coding categories
    """
    if output_path is None:
        output_path = str(FIGURES_DIR / "pairwise_analysis.png")
    
    # Filter valid data
    analysis_data = buildings_gdf[
        (buildings_gdf[column].notna()) & 
        (buildings_gdf[column] > 0)
    ].copy()
    
    if analysis_data.empty:
        print(f"No valid data for pairwise analysis")
        return
    
    # Create categories if hue_column not provided
    if hue_column is None:
        quantiles = analysis_data[column].quantile([0, 0.2, 0.4, 0.6, 0.8, 1.0])
        
        def categorize(value):
            if value <= quantiles[0.2]:
                return 'Very Low'
            elif value <= quantiles[0.4]:
                return 'Low'
            elif value <= quantiles[0.6]:
                return 'Mid'
            elif value <= quantiles[0.8]:
                return 'High'
            else:
                return 'Very High'
        
        analysis_data['category'] = analysis_data[column].apply(categorize)
        hue_column = 'category'
    
    # Select numeric columns for pairplot
    numeric_cols = [column]
    for col in ['roof_area_m2', 'roof_orientation_deg', 'b3_h_max', 'num_vertices']:
        if col in analysis_data.columns:
            numeric_cols.append(col)
    
    numeric_cols.append(hue_column)
    
    # Create pairplot
    sns.set_theme(style="ticks")
    pairplot_data = analysis_data[numeric_cols].copy()
    
    g = sns.pairplot(pairplot_data, hue=hue_column, diag_kind='kde', corner=False)
    g.fig.suptitle('Pairwise Analysis of Building Characteristics', y=1.02, fontsize=16, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', dpi=300)
    plt.close()
    
    print(f"Pairwise analysis saved to: {output_path}")
    
    # Print summary statistics
    print(f"\n=== GROUPED ANALYSIS BY {hue_column.upper()} ===")
    grouped = analysis_data.groupby(hue_column)[numeric_cols[:-1]].mean().round(2)
    print(grouped)


def create_top_buildings_map(
    buildings_gdf: gpd.GeoDataFrame,
    column: str = 'solar_potential_kwh',
    top_n: int = 100,
    output_path: Optional[str] = None,
    zoom_start: int = 13
) -> Optional[object]:
    """
    Create an interactive map showing top N priority buildings.
    
    Parameters
    ----------
    buildings_gdf : gpd.GeoDataFrame
        GeoDataFrame with building data
    column : str
        Column to rank by
    top_n : int
        Number of top buildings to show
    output_path : str, optional
        Path to save HTML file
    zoom_start : int
        Initial zoom level
    
    Returns
    -------
    folium.Map or None
    """
    if not FOLIUM_AVAILABLE:
        print("Error: folium not installed")
        return None
    
    if output_path is None:
        output_path = str(MAPS_DIR / f"top_{top_n}_buildings.html")
    
    # Get top N buildings
    top_buildings = buildings_gdf.nlargest(top_n, column).copy()
    
    # Convert to WGS84
    if top_buildings.crs != 'EPSG:4326':
        top_buildings = top_buildings.to_crs('EPSG:4326')
    
    # Drop non-serializable columns (timestamps, complex objects)
    cols_to_drop = []
    for col in top_buildings.columns:
        if col != 'geometry' and col != column:
            try:
                # Check if column contains timestamp or other non-serializable types
                if top_buildings[col].dtype == 'object':
                    # Try to serialize a sample
                    import json
                    json.dumps(top_buildings[col].iloc[0] if len(top_buildings) > 0 else None)
            except (TypeError, AttributeError):
                cols_to_drop.append(col)
    
    # Keep only geometry and the column we're displaying
    top_buildings_simple = top_buildings[[column, 'geometry']].copy()
    
    # Get map center using bounds (better for geographic coordinates)
    bounds = top_buildings_simple.total_bounds  # [minx, miny, maxx, maxy]
    center_lon = (bounds[0] + bounds[2]) / 2
    center_lat = (bounds[1] + bounds[3]) / 2
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        tiles='Esri.WorldImagery'
    )
    
    # Add all buildings as a single GeoJson layer (much faster)
    folium.GeoJson(
        top_buildings_simple,
        style_function=lambda x: {
            'fillColor': '#FF0000',
            'color': '#FF0000',
            'weight': 1,
            'fillOpacity': 0.7
        },
        tooltip=folium.GeoJsonTooltip(fields=[column], aliases=[column.replace('_', ' ').title()])
    ).add_to(m)
    
    # Save map
    m.save(output_path)
    print(f"Top {top_n} buildings map saved to: {output_path}")
    
    return m


# ============================================================================
# Original Map Generation Functions
# ============================================================================

def plot_suitability_map(
    buildings_gdf: gpd.GeoDataFrame,
    suitability_column: str = 'suitability_score',
    output_path: Optional[str] = None,
    title: str = "Solar Panel Suitability Map",
    figsize: Tuple[int, int] = (15, 12),
    cmap: str = 'RdYlGn',
    show_legend: bool = True
) -> None:
    """
    Create a choropleth map showing building suitability scores.
    
    Parameters
    ----------
    buildings_gdf : gpd.GeoDataFrame
        GeoDataFrame with building geometries and suitability scores
    suitability_column : str
        Column name containing suitability scores
    output_path : str, optional
        Path to save the map. If None, saves to outputs/maps/
    title : str
        Map title
    figsize : tuple
        Figure size (width, height)
    cmap : str
        Matplotlib colormap name
    show_legend : bool
        Whether to show the legend
    """
    if output_path is None:
        output_path = MAPS_DIR / "suitability_map.png"
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Plot buildings with color based on suitability
    buildings_gdf.plot(
        column=suitability_column,
        ax=ax,
        cmap=cmap,
        edgecolor='black',
        linewidth=0.1,
        legend=show_legend,
        legend_kwds={'label': 'Suitability Score', 'shrink': 0.8}
    )
    
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Longitude', fontsize=12)
    ax.set_ylabel('Latitude', fontsize=12)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()
    
    print(f"Suitability map saved to: {output_path}")


def plot_solar_irradiance_map(
    buildings_gdf: gpd.GeoDataFrame,
    irradiance_column: str = 'solar_irradiance',
    output_path: Optional[str] = None,
    title: str = "Solar Irradiance Distribution",
    figsize: Tuple[int, int] = (15, 12)
) -> None:
    """
    Create a map showing solar irradiance distribution.
    
    Parameters
    ----------
    buildings_gdf : gpd.GeoDataFrame
        GeoDataFrame with building geometries and irradiance values
    irradiance_column : str
        Column name containing irradiance values
    output_path : str, optional
        Path to save the map
    title : str
        Map title
    figsize : tuple
        Figure size
    """
    if output_path is None:
        output_path = MAPS_DIR / "solar_irradiance_map.png"
    
    fig, ax = plt.subplots(figsize=figsize)
    
    buildings_gdf.plot(
        column=irradiance_column,
        ax=ax,
        cmap='YlOrRd',
        edgecolor='black',
        linewidth=0.1,
        legend=True,
        legend_kwds={'label': 'Solar Irradiance (W/m²)', 'shrink': 0.8}
    )
    
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Longitude', fontsize=12)
    ax.set_ylabel('Latitude', fontsize=12)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()
    
    print(f"Solar irradiance map saved to: {output_path}")


def plot_categorical_map(
    buildings_gdf: gpd.GeoDataFrame,
    category_column: str,
    output_path: Optional[str] = None,
    title: Optional[str] = None,
    figsize: Tuple[int, int] = (15, 12),
    color_map: Optional[Dict[str, str]] = None
) -> None:
    """
    Create a categorical map (e.g., suitability classes, roof types).
    
    Parameters
    ----------
    buildings_gdf : gpd.GeoDataFrame
        GeoDataFrame with building geometries
    category_column : str
        Column name containing categorical values
    output_path : str, optional
        Path to save the map
    title : str, optional
        Map title
    figsize : tuple
        Figure size
    color_map : dict, optional
        Mapping of categories to colors
    """
    if output_path is None:
        output_path = MAPS_DIR / f"{category_column}_map.png"
    
    if title is None:
        title = f"{category_column.replace('_', ' ').title()} Distribution"
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Get unique categories
    categories = buildings_gdf[category_column].unique()
    
    # Create color map if not provided
    if color_map is None:
        colors = plt.cm.Set3(np.linspace(0, 1, len(categories)))
        color_map = dict(zip(categories, colors))
    
    # Plot each category
    for category in categories:
        subset = buildings_gdf[buildings_gdf[category_column] == category]
        subset.plot(ax=ax, color=color_map[category], edgecolor='black', 
                   linewidth=0.1, label=category)
    
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Longitude', fontsize=12)
    ax.set_ylabel('Latitude', fontsize=12)
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()
    
    print(f"Categorical map saved to: {output_path}")


# ============================================================================
# Statistical Figures
# ============================================================================

def plot_suitability_distribution(
    buildings_gdf: gpd.GeoDataFrame,
    suitability_column: str = 'suitability_score',
    output_path: Optional[str] = None,
    bins: int = 50
) -> None:
    """
    Create histogram of suitability scores.
    
    Parameters
    ----------
    buildings_gdf : gpd.GeoDataFrame
        GeoDataFrame with suitability scores
    suitability_column : str
        Column name containing suitability scores
    output_path : str, optional
        Path to save the figure
    bins : int
        Number of histogram bins
    """
    if output_path is None:
        output_path = FIGURES_DIR / "suitability_distribution.png"
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    scores = buildings_gdf[suitability_column].dropna()
    
    ax.hist(scores, bins=bins, color='steelblue', edgecolor='black', alpha=0.7)
    ax.axvline(scores.mean(), color='red', linestyle='--', linewidth=2, 
               label=f'Mean: {scores.mean():.2f}')
    ax.axvline(scores.median(), color='green', linestyle='--', linewidth=2, 
               label=f'Median: {scores.median():.2f}')
    
    ax.set_xlabel('Suitability Score', fontsize=12)
    ax.set_ylabel('Number of Buildings', fontsize=12)
    ax.set_title('Distribution of Suitability Scores', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()
    
    print(f"Distribution plot saved to: {output_path}")


def plot_top_buildings(
    buildings_gdf: gpd.GeoDataFrame,
    suitability_column: str = 'suitability_score',
    top_n: int = 20,
    output_path: Optional[str] = None
) -> None:
    """
    Create bar chart of top N most suitable buildings.
    
    Parameters
    ----------
    buildings_gdf : gpd.GeoDataFrame
        GeoDataFrame with building data
    suitability_column : str
        Column name containing suitability scores
    top_n : int
        Number of top buildings to show
    output_path : str, optional
        Path to save the figure
    """
    if output_path is None:
        output_path = FIGURES_DIR / f"top_{top_n}_buildings.png"
    
    # Get top N buildings
    top_buildings = buildings_gdf.nlargest(top_n, suitability_column)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Create bar chart
    bars = ax.barh(range(top_n), top_buildings[suitability_column].values, 
                   color='forestgreen', edgecolor='black')
    
    # Add building IDs as labels if available
    if 'building_id' in top_buildings.columns:
        labels = top_buildings['building_id'].astype(str).values
    else:
        labels = [f"Building {i+1}" for i in range(top_n)]
    
    ax.set_yticks(range(top_n))
    ax.set_yticklabels(labels)
    ax.set_xlabel('Suitability Score', fontsize=12)
    ax.set_ylabel('Building ID', fontsize=12)
    ax.set_title(f'Top {top_n} Most Suitable Buildings for Solar Panels', 
                 fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')
    
    # Add value labels on bars
    for i, bar in enumerate(bars):
        width = bar.get_width()
        ax.text(width, bar.get_y() + bar.get_height()/2, 
                f'{width:.2f}', ha='left', va='center', fontsize=8)
    
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()
    
    print(f"Top buildings chart saved to: {output_path}")


def plot_scatter_analysis(
    buildings_gdf: gpd.GeoDataFrame,
    x_column: str,
    y_column: str,
    output_path: Optional[str] = None,
    title: Optional[str] = None
) -> None:
    """
    Create scatter plot for analyzing relationships between variables.
    
    Parameters
    ----------
    buildings_gdf : gpd.GeoDataFrame
        GeoDataFrame with building data
    x_column : str
        Column name for x-axis
    y_column : str
        Column name for y-axis
    output_path : str, optional
        Path to save the figure
    title : str, optional
        Plot title
    """
    if output_path is None:
        output_path = FIGURES_DIR / f"{x_column}_vs_{y_column}.png"
    
    if title is None:
        title = f"{y_column.replace('_', ' ').title()} vs {x_column.replace('_', ' ').title()}"
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    ax.scatter(buildings_gdf[x_column], buildings_gdf[y_column], 
              alpha=0.5, c='steelblue', edgecolors='black', linewidth=0.5)
    
    ax.set_xlabel(x_column.replace('_', ' ').title(), fontsize=12)
    ax.set_ylabel(y_column.replace('_', ' ').title(), fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # Add correlation coefficient
    corr = buildings_gdf[[x_column, y_column]].corr().iloc[0, 1]
    ax.text(0.05, 0.95, f'Correlation: {corr:.3f}', 
            transform=ax.transAxes, fontsize=12,
            verticalalignment='top', bbox=dict(boxstyle='round', 
            facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()
    
    print(f"Scatter plot saved to: {output_path}")


# ============================================================================
# Report Generation
# ============================================================================

def generate_summary_report(
    buildings_gdf: gpd.GeoDataFrame,
    suitability_column: str = 'suitability_score',
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a summary statistics report.
    
    Parameters
    ----------
    buildings_gdf : gpd.GeoDataFrame
        GeoDataFrame with building data
    suitability_column : str
        Column name containing suitability scores
    output_path : str, optional
        Path to save the report
        
    Returns
    -------
    dict
        Dictionary containing summary statistics
    """
    if output_path is None:
        output_path = REPORTS_DIR / "summary_report.txt"
    
    scores = buildings_gdf[suitability_column].dropna()
    
    # Calculate statistics
    stats = {
        'total_buildings': len(buildings_gdf),
        'buildings_with_scores': len(scores),
        'mean_score': scores.mean(),
        'median_score': scores.median(),
        'std_score': scores.std(),
        'min_score': scores.min(),
        'max_score': scores.max(),
        'q25': scores.quantile(0.25),
        'q75': scores.quantile(0.75)
    }
    
    # Count highly suitable buildings (score > 0.7)
    if scores.max() > 1:  # If scores are not normalized
        threshold = 0.7 * scores.max()
    else:
        threshold = 0.7
    
    stats['highly_suitable'] = (scores > threshold).sum()
    stats['highly_suitable_pct'] = (stats['highly_suitable'] / len(scores)) * 100
    
    # Generate report text
    report = f"""
Solar Panel Suitability Analysis - Summary Report
{'='*60}

Dataset Overview:
  Total Buildings: {stats['total_buildings']:,}
  Buildings with Scores: {stats['buildings_with_scores']:,}

Suitability Score Statistics:
  Mean:     {stats['mean_score']:.4f}
  Median:   {stats['median_score']:.4f}
  Std Dev:  {stats['std_score']:.4f}
  Min:      {stats['min_score']:.4f}
  Max:      {stats['max_score']:.4f}
  Q1 (25%): {stats['q25']:.4f}
  Q3 (75%): {stats['q75']:.4f}

Highly Suitable Buildings (score > {threshold:.2f}):
  Count: {stats['highly_suitable']:,}
  Percentage: {stats['highly_suitable_pct']:.2f}%

{'='*60}
Report generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    # Save report
    with open(output_path, 'w') as f:
        f.write(report)
    
    print(f"Summary report saved to: {output_path}")
    print(report)
    
    return stats


def create_visualization_suite(
    buildings_gdf: gpd.GeoDataFrame,
    suitability_column: str = 'suitability_score',
    output_dir: Optional[str] = None
) -> None:
    """
    Generate a complete suite of visualizations.
    
    Parameters
    ----------
    buildings_gdf : gpd.GeoDataFrame
        GeoDataFrame with building data and suitability scores
    suitability_column : str
        Column name containing suitability scores
    output_dir : str, optional
        Base directory for outputs
    """
    print("\nGenerating visualization suite...")
    print("=" * 60)
    
    # Generate all visualizations
    plot_suitability_map(buildings_gdf, suitability_column)
    plot_suitability_distribution(buildings_gdf, suitability_column)
    plot_top_buildings(buildings_gdf, suitability_column)
    
    # Generate summary report
    generate_summary_report(buildings_gdf, suitability_column)
    
    print("=" * 60)
    print("Visualization suite complete!")


# ============================================================================
# Main execution
# ============================================================================

if __name__ == "__main__":
    """
    Standalone execution: Generate visualizations for both test and full datasets.
    
    Usage:
        python src/visualization.py
    
    Generates two sets of visualizations:
    1. Test dataset (ranked_test_buildings.json) - default names
    2. Full Amsterdam dataset (ranked_buildings.json) - names with '_amsterdam' suffix
    
    Outputs:
        Test dataset:
            - suitability_map.png, solar_potential_choropleth.png, etc.
        Full Amsterdam:
            - suitability_map_amsterdam.png, solar_potential_choropleth_amsterdam.png, etc.
    """
    import sys
    
    print("=" * 70)
    print("SOLAR PANEL SUITABILITY MAPPING - VISUALIZATION SUITE")
    print("=" * 70)
    print(f"\nOutput directories:")
    print(f"  📊 Figures: {FIGURES_DIR}")
    print(f"  🗺️  Maps: {MAPS_DIR}")
    print(f"  📄 Reports: {REPORTS_DIR}")
    
    # Define datasets to process (only test dataset for performance)
    datasets = [
        {
            'name': 'Test Dataset',
            'path': Path("data/ranked_test_buildings.json"),
            'suffix': '',  # Default names
            'top_n': 20,
            'zoom': 13
        }
    ]
    
    for dataset_config in datasets:
        dataset_name = dataset_config['name']
        data_path = dataset_config['path']
        suffix = dataset_config['suffix']
        top_n = dataset_config['top_n']
        zoom = dataset_config['zoom']
        
        print("\n" + "=" * 70)
        print(f"PROCESSING: {dataset_name.upper()}")
        print("=" * 70)
        
        if not data_path.exists():
            print(f"\n⚠️  Skipping {dataset_name}: File not found")
            print(f"   Expected: {data_path}")
            continue
        
        try:
            # Load ranked buildings
            print(f"\n📂 Loading data from: {data_path}")
            buildings = gpd.read_file(data_path)
            
            print(f"✓ Loaded {len(buildings)} buildings")
            print(f"✓ CRS: {buildings.crs}")
            print(f"✓ Columns: {', '.join(buildings.columns[:8])}...")
            
            # Normalize column names to handle different naming conventions
            # Create mapping from alternate names to standard names
            if 'solar_energy_kwh_year' in buildings.columns and 'energy_potential' not in buildings.columns:
                buildings = buildings.rename(columns={'solar_energy_kwh_year': 'energy_potential'})
                print("   ✓ Normalized: solar_energy_kwh_year → energy_potential")
            
            if 'roof_area_m2' in buildings.columns and 'roof_area' not in buildings.columns:
                buildings = buildings.rename(columns={'roof_area_m2': 'roof_area'})
                print("   ✓ Normalized: roof_area_m2 → roof_area")
            
            if 'roof_orientation_deg' in buildings.columns and 'orientation' not in buildings.columns:
                buildings = buildings.rename(columns={'roof_orientation_deg': 'orientation'})
                print("   ✓ Normalized: roof_orientation_deg → orientation")
            
            # Check for required columns
            required_cols = ['suitability_score']
            missing_cols = [col for col in required_cols if col not in buildings.columns]
            
            if missing_cols:
                print(f"\n⚠️  Warning: Missing columns: {missing_cols}")
                print("   Some visualizations may not work correctly.")
            
            # Generate all visualizations
            print(f"\n{'─' * 70}")
            print(f"GENERATING VISUALIZATIONS FOR {dataset_name.upper()}")
            print(f"{'─' * 70}")
            
            # 1. Suitability map
            print("\n1️⃣  Generating suitability map...")
            plot_suitability_map(
                buildings, 
                suitability_column='suitability_score',
                output_path=str(MAPS_DIR / f"suitability_map{suffix}.png")
            )
            print(f"   ✓ Saved: {MAPS_DIR / f'suitability_map{suffix}.png'}")
            
            # 2. Solar potential choropleth
            if 'energy_potential' in buildings.columns:
                print("\n2️⃣  Generating solar potential choropleth...")
                plot_solar_potential_choropleth(
                    buildings,
                    column='energy_potential',
                    output_path=str(MAPS_DIR / f"solar_potential_choropleth{suffix}.png"),
                    title=f'{dataset_name} - Building-level Energy Potential',
                    cmap='autumn',
                    figsize=(14, 12),
                    dark_theme=True
                )
                print(f"   ✓ Saved: {MAPS_DIR / f'solar_potential_choropleth{suffix}.png'}")
            else:
                print("\n2️⃣  Skipping solar potential choropleth (column not found)")
            
            # 3. Interactive Folium map
            if FOLIUM_AVAILABLE and 'energy_potential' in buildings.columns:
                print("\n3️⃣  Generating interactive Folium map...")
                create_interactive_folium_map(
                    buildings,
                    column='energy_potential',
                    output_path=str(MAPS_DIR / f"solar_interactive_map{suffix}.html"),
                    zoom_start=zoom,
                    tiles='Esri.WorldImagery'
                )
                print(f"   ✓ Saved: {MAPS_DIR / f'solar_interactive_map{suffix}.html'}")
            else:
                if not FOLIUM_AVAILABLE:
                    print("\n3️⃣  Skipping interactive map (folium not installed)")
                else:
                    print("\n3️⃣  Skipping interactive map (energy_potential column not found)")
            
            # 4. Statistical summary
            print("\n4️⃣  Generating statistical summary...")
            plot_suitability_distribution(
                buildings,
                suitability_column='suitability_score',
                output_path=str(FIGURES_DIR / f"statistical_summary{suffix}.png")
            )
            print(f"   ✓ Saved: {FIGURES_DIR / f'statistical_summary{suffix}.png'}")
            
            # 5. Pairwise analysis
            if 'energy_potential' in buildings.columns:
                print("\n5️⃣  Generating pairwise analysis...")
                plot_pairwise_analysis(
                    buildings,
                    column='energy_potential',
                    output_path=str(FIGURES_DIR / f"pairwise_analysis{suffix}.png"),
                    hue_column='suitability_class' if 'suitability_class' in buildings.columns else None
                )
                print(f"   ✓ Saved: {FIGURES_DIR / f'pairwise_analysis{suffix}.png'}")
            else:
                print("\n5️⃣  Skipping pairwise analysis (energy_potential column not found)")
            
            # 6. Top N buildings chart
            print(f"\n6️⃣  Generating top {top_n} buildings chart...")
            plot_top_buildings(
                buildings,
                suitability_column='suitability_score',
                top_n=min(top_n, len(buildings)),
                output_path=str(FIGURES_DIR / f"top_{top_n}_buildings{suffix}.png")
            )
            print(f"   ✓ Saved: {FIGURES_DIR / f'top_{top_n}_buildings{suffix}.png'}")
            
            # 8. Top N buildings interactive map
            if FOLIUM_AVAILABLE and 'energy_potential' in buildings.columns:
                print(f"\n8️⃣  Generating top {top_n} buildings map...")
                create_top_buildings_map(
                    buildings,
                    column='energy_potential',
                    top_n=min(top_n, len(buildings)),
                    output_path=str(MAPS_DIR / f"top_{top_n}_buildings{suffix}.html"),
                    zoom_start=zoom
                )
                print(f"   ✓ Saved: {MAPS_DIR / f'top_{top_n}_buildings{suffix}.html'}")
            else:
                print(f"\n8️⃣  Skipping top {top_n} buildings map")
            
            # 9. Generate CSV report
            print(f"\n9️⃣  Generating CSV priority list (top {top_n})...")
            top_buildings = buildings.nlargest(min(top_n, len(buildings)), 'suitability_score')
            
            # Select relevant columns for report
            report_cols = ['suitability_score']
            if 'suitability_class' in buildings.columns:
                report_cols.append('suitability_class')
            if 'rank' in buildings.columns:
                report_cols.insert(0, 'rank')
            if 'identificatie' in buildings.columns:
                report_cols.insert(0, 'identificatie')
            if 'roof_area' in buildings.columns:
                report_cols.append('roof_area')
            if 'energy_potential' in buildings.columns:
                report_cols.append('energy_potential')
            if 'orientation' in buildings.columns:
                report_cols.append('orientation')
            if 'shading_factor' in buildings.columns:
                report_cols.append('shading_factor')
            
            # Filter report_cols to only include columns that exist
            report_cols = [col for col in report_cols if col in buildings.columns]
            
            # Save to CSV (drop geometry for CSV)
            csv_path = REPORTS_DIR / f"top_{top_n}_priority_buildings{suffix}.csv"
            top_buildings_data = top_buildings[report_cols].copy()
            top_buildings_data.to_csv(csv_path, index=False)
            print(f"   ✓ Saved: {csv_path}")
            
            # 10. Generate JSON summary report
            print("\n🔟  Generating JSON summary report...")
            generate_summary_report(
                buildings,
                suitability_column='suitability_score',
                output_path=str(REPORTS_DIR / f"summary_report{suffix}.json")
            )
            print(f"   ✓ Saved: {REPORTS_DIR / f'summary_report{suffix}.json'}")
            
            # Dataset summary
            print(f"\n{'─' * 70}")
            print(f"✅ {dataset_name.upper()} COMPLETE!")
            print(f"{'─' * 70}")
            
        except Exception as e:
            print(f"\n❌ ERROR processing {dataset_name}: {e}")
            import traceback
            print("\nFull traceback:")
            traceback.print_exc()
            continue
    
    # Final summary
    print("\n" + "=" * 70)
    print("✅ ALL VISUALIZATIONS GENERATED!")
    print("=" * 70)
    print(f"\n📊 Output locations:")
    print(f"   • Figures: {FIGURES_DIR}")
    print(f"   • Maps: {MAPS_DIR}")
    print(f"   • Reports: {REPORTS_DIR}")
    print(f"\n💡 File naming:")
    print(f"   • Test dataset: Default names (e.g., suitability_map.png)")
    print(f"   • Full Amsterdam: Names with '_amsterdam' suffix (e.g., suitability_map_amsterdam.png)")

