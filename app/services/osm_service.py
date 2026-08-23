"""
OpenStreetMap service for downloading and processing road network data.
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

import osmnx as ox
import geopandas as gpd
from shapely.geometry import LineString, MultiLineString
from shapely.ops import unary_union
import numpy as np

from app.core.config import get_settings

settings = get_settings()


class OSMService:
    """
    Service for interacting with OpenStreetMap data via OSMnx.
    """
    
    def __init__(self):
        self.place = settings.OSM_PLACE
        self.network_type = settings.OSM_NETWORK_TYPE
        self._edges_gdf: Optional[gpd.GeoDataFrame] = None
    
    def load_road_network(self) -> gpd.GeoDataFrame:
        """
        Download and process road network from OpenStreetMap.
        
        Returns:
            GeoDataFrame with processed edges including length in meters.
        """
        print(f"Downloading road network for: {self.place}")
        print("   (this may take 1-3 minutes on first run)")
        
        # Download the drivable road graph
        graph = ox.graph_from_place(
            self.place,
            network_type=self.network_type,
            simplify=True
        )
        
        # Convert to GeoDataFrames
        nodes_gdf, edges_gdf = ox.graph_to_gdfs(graph, nodes=True, edges=True)
        
        # Project to metric CRS for accurate length calculation
        edges_proj = ox.projection.project_gdf(edges_gdf)
        
        # Calculate length in meters
        edges_proj["length_m"] = edges_proj.geometry.length
        
        self._edges_gdf = edges_proj
        
        print(f"Loaded {len(edges_proj)} road segments")
        return edges_proj
    
    def get_edges_gdf(self) -> Optional[gpd.GeoDataFrame]:
        """Get cached edges GeoDataFrame."""
        return self._edges_gdf
    
    def search_roads(
        self,
        query: str,
        exact_match: bool = False
    ) -> gpd.GeoDataFrame:
        """
        Search for roads by name or reference.
        
        Args:
            query: Search query string
            exact_match: If True, requires exact match; otherwise partial match
            
        Returns:
            Filtered GeoDataFrame with matching roads
        """
        if self._edges_gdf is None:
            raise ValueError("Road network not loaded. Call load_road_network() first.")
        
        # Normalize query
        target = re.sub(r"\s+", " ", query.strip()).lower()
        
        if not target:
            return gpd.GeoDataFrame()
        
        def match_value(value) -> bool:
            """Check if value matches query."""
            if isinstance(value, list):
                return any(match_value(v) for v in value)
            if isinstance(value, str):
                normalized = re.sub(r"\s+", " ", value.strip()).lower()
                if exact_match:
                    return normalized == target
                return target in normalized
            return False
        
        # Search in name and ref columns
        name_mask = self._edges_gdf.get("name", pd.Series([None] * len(self._edges_gdf))).apply(match_value)
        ref_mask = self._edges_gdf.get("ref", pd.Series([None] * len(self._edges_gdf))).apply(match_value)
        
        combined_mask = name_mask | ref_mask
        return self._edges_gdf.loc[combined_mask]
    
    def aggregate_road_data(
        self,
        edges: gpd.GeoDataFrame
    ) -> Dict[str, Any]:
        """
        Aggregate road data from multiple segments.
        
        Args:
            edges: GeoDataFrame of road segments
            
        Returns:
            Dictionary with aggregated road information
        """
        if edges.empty:
            return {}
        
        # Get primary name (most common)
        names = edges["name"].dropna()#['rfr','rfrfr','','rfrfrf']
        primary_name = "Unknown"
        if not names.empty:
            mode_result = names.mode()#[1,2,3,3,3,4,4,4,5,6]
            if len(mode_result) > 0:
                val = mode_result[0]
                # Handle if mode returns array
                if isinstance(val, np.ndarray):
                    val = str(val[0]) if val.size > 0 else "Unknown"
                primary_name = str(val) if val is not None else "Unknown"
        
        # Get reference (road number like A487)
        refs = edges["ref"].dropna()
        primary_ref = None
        if not refs.empty:
            mode_result = refs.mode()
            if len(mode_result) > 0:
                val = mode_result[0]
                # Handle if mode returns array
                if isinstance(val, np.ndarray):
                    val = str(val[0]) if val.size > 0 else None
                primary_ref = str(val) if val is not None else None
        
        # Collect unique road types
        road_types = self._collect_unique_values(edges, "highway")
        primary_type = road_types[0] if road_types else None
        
        # Speed limits
        speed_limits = self._collect_unique_values(edges, "maxspeed")
        primary_speed = speed_limits[0] if speed_limits else None
        
        # Surface types
        surfaces = self._collect_unique_values(edges, "surface")
        primary_surface = surfaces[0] if surfaces else None
        
        # Total length
        total_length = edges["length_m"].sum()
        
        # Get start and end points
        first_geom = edges.geometry.iloc[0]
        last_geom = edges.geometry.iloc[-1]
        
        # Convert back to WGS84 for coordinates
        start_coord = self._get_first_coordinate(first_geom)
        end_coord = self._get_last_coordinate(last_geom)
        
        # Calculate bounding box
        bounds = edges.total_bounds  # (minx, miny, maxx, maxy)
        
        # Helper to convert numpy values to Python native types
        def to_python(val):
            if val is None:
                return None
            if isinstance(val, np.ndarray):
                return val.item() if val.size == 1 else float(val[0]) if val.size > 0 else None
            if isinstance(val, (np.integer, np.floating)):
                return val.item()
            return val
        
        # Center point
        center_x = (bounds[0] + bounds[2]) / 2
        center_y = (bounds[1] + bounds[3]) / 2
        
        # Convert center to WGS84
        center_lon, center_lat = self._projected_to_wgs84(center_x, center_y, edges.crs)
        
        return {
            "name": primary_name,
            "ref": primary_ref,
            "road_type": primary_type,
            "total_length_m": to_python(round(total_length, 2)),
            "segment_count": len(edges),
            "speed_limit": primary_speed,
            "surface_type": primary_surface,
            "start_point": [to_python(coord) for coord in start_coord],
            "end_point": [to_python(coord) for coord in end_coord],
            "bbox": {
                "west": to_python(bounds[0]),
                "south": to_python(bounds[1]),
                "east": to_python(bounds[2]),
                "north": to_python(bounds[3])
            },
            "center_lat": to_python(center_lat),
            "center_lon": to_python(center_lon),
            "all_road_types": road_types,
            "all_speed_limits": speed_limits,
            "all_surfaces": surfaces
        }
    
    def _collect_unique_values(self, gdf: gpd.GeoDataFrame, column: str) -> List[str]:
        """Collect unique non-null values from a column."""
        if column not in gdf.columns:
            return []
        
        import numpy as np
        unique = set()
        for value in gdf[column].dropna():
            if isinstance(value, (list, np.ndarray)):
                for v in value:
                    unique.add(str(v).strip())
            else:
                unique.add(str(value).strip())
        
        unique.discard("")
        unique.discard("nan")
        return sorted(unique)
    
    def _get_first_coordinate(self, geometry) -> List[float]:
        """Get first coordinate as [lat, lon] in WGS84."""
        try:
            coords = list(geometry.coords)
            if coords:
                x, y = coords[0]
                # Check if geometry has CRS info
                source_crs = None
                if hasattr(geometry, 'crs') and geometry.crs:
                    source_crs = str(geometry.crs)
                
                # If already WGS84 or no CRS, return as-is
                if source_crs and ('4326' in source_crs or 'WGS84' in source_crs):
                    return [round(y, 6), round(x, 6)]  # [lat, lon]
                
                return self._projected_to_wgs84(x, y, source_crs)
        except Exception as e:
            print(f"Error getting first coordinate: {e}")
        return [0.0, 0.0]
    
    def _get_last_coordinate(self, geometry) -> List[float]:
        """Get last coordinate as [lat, lon] in WGS84."""
        try:
            coords = list(geometry.coords)
            if coords:
                x, y = coords[-1]
                # Check if geometry has CRS info
                source_crs = None
                if hasattr(geometry, 'crs') and geometry.crs:
                    source_crs = str(geometry.crs)
                
                # If already WGS84 or no CRS, return as-is
                if source_crs and ('4326' in source_crs or 'WGS84' in source_crs):
                    return [round(y, 6), round(x, 6)]  # [lat, lon]
                
                return self._projected_to_wgs84(x, y, source_crs)
        except Exception as e:
            print(f"Error getting last coordinate: {e}")
        return [0.0, 0.0]
    
    def _projected_to_wgs84(
        self,
        x: float,
        y: float,
        source_crs: Optional[Any]
    ) -> List[float]:
        """Convert projected coordinates to WGS84 [lat, lon]."""
        try:
            from shapely.ops import transform
            from pyproj import Transformer
            
            if source_crs is None:
                # Assume UTM or similar metric CRS for Gwynedd area
                source_crs = "EPSG:32630"  # UTM zone 30N
            
            transformer = Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)
            lon, lat = transformer.transform(x, y)
            return [round(lat, 6), round(lon, 6)]
        except Exception as e:
            print(f"CRS conversion error: {e}")
            return [round(y, 6), round(x, 6)]  # Fallback: assume input was lat/lon
    
    def get_segment_details(
        self,
        edges: gpd.GeoDataFrame
    ) -> List[Dict[str, Any]]:
        """Extract detailed information for each segment."""
        segments = []
        
        for idx, row in edges.iterrows():
            geom = row.geometry
            coords = list(geom.coords)
            
            # Get coordinates for geometry
            start_pt = self._get_first_coordinate(geom)
            end_pt = self._get_last_coordinate(geom)
            
            segment = {
                "osm_id": str(idx) if not isinstance(idx, tuple) else f"{idx[0]}_{idx[1]}",
                "length_m": round(row.get("length_m", 0), 2),
                "road_type": row.get("highway"),
                "maxspeed": row.get("maxspeed"),
                "surface": row.get("surface"),
                "lanes": row.get("lanes"),
                "width": row.get("width"),
                "osm_name": row.get("name"),
                "osm_ref": row.get("ref"),
                "start_point": start_pt,
                "end_point": end_pt,
                "geometry": geom,  # Add geometry for database insertion
                "raw_tags": {
                    k: v for k, v in row.items()
                    if k not in ["geometry", "length_m"] and pd.notna(v)
                }
            }
            segments.append(segment)
        
        return segments


# Import pandas for type hinting
import pandas as pd
