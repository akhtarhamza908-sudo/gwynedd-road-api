"""
Data synchronization service for importing OSM data into the database.
"""
from typing import List, Dict, Any, Optional
import asyncio
from sqlalchemy.orm import Session

import geopandas as gpd
import pandas as pd
import numpy as np
from geoalchemy2.shape import from_shape
from shapely.geometry import LineString, MultiLineString

from app.core.config import get_settings
from app.models.road import Road
from app.models.segment import RoadSegment
from app.schemas.road import RoadCreate
from app.schemas.segment import SegmentCreate
from app.services.osm_service import OSMService
from app.services.road_service import RoadService
from app.services.geometry_service import GeometryAnalysisService
from app.utils.elevation import ElevationService

settings = get_settings()


class DataSyncService:
    """
    Service for synchronizing OpenStreetMap data to the database.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.osm_service = OSMService()
        self.road_service = RoadService(db)
        self.geometry_service = GeometryAnalysisService()
        self.elevation_service = ElevationService()
    
    async def sync_all_roads(self, batch_size: int = 100) -> Dict[str, Any]:
        """
        Sync all roads from OSM to the database.
        
        This is a one-time import operation that:
        1. Downloads the full road network
        2. Groups segments by road name
        3. Creates Road and RoadSegment records
        4. Performs geometry analysis
        
        Returns:
            Statistics about the sync operation
        """
        print("Starting OSM data synchronization...")
        
        # Load road network
        edges_gdf = self.osm_service.load_road_network()
        
        # Group edges by road name
        road_groups = self._group_edges_by_road(edges_gdf)
        
        stats = {
            "roads_processed": 0,
            "segments_processed": 0,
            "roads_created": 0,
            "errors": []
        }
        
        # Process each road group
        for road_name, edges in road_groups.items():
            try:
                # Create road with segments
                road = await self._create_road_with_segments(edges, {"name": road_name})
                stats["roads_processed"] += 1
                stats["segments_processed"] += len(edges)
                
                if stats["roads_processed"] % 100 == 0:
                    print(f"Processed {stats['roads_processed']} roads...")
                
            except Exception as e:
                error_msg = f"Error processing road '{road_name}': {str(e)}"
                print(error_msg)
                stats["errors"].append(error_msg)
        
        stats["roads_created"] = stats["roads_processed"] - len(stats["errors"])
        
        print(f"Sync complete. Processed {stats['roads_processed']} roads with {stats['segments_processed']} segments.")
        
        return stats
    
    def _group_edges_by_road(
        self,
        edges_gdf: gpd.GeoDataFrame
    ) -> Dict[str, gpd.GeoDataFrame]:
        """
        Group road edges by their primary name.
        
        Returns:
            Dictionary mapping road name to GeoDataFrame of segments
        """
        import pandas as pd
        road_groups = {}
        
        # Helper function to safely convert to hashable string
        import numpy as np
        def to_hashable(val):
            if val is None:
                return None
            # Handle numpy arrays - check if it's an array first
            if isinstance(val, np.ndarray):
                return str(val[0]) if val.size > 0 else None
            # Handle pandas NA/NaN - use try/except to avoid array ambiguity
            try:
                if pd.isna(val):
                    return None
            except ValueError:
                # pd.isna raised error (e.g., for arrays), convert to string
                return str(val)
            if isinstance(val, list):
                return str(val[0]) if len(val) > 0 else None
            return str(val)
        
        # Group by name
        if "name" in edges_gdf.columns:
            # Convert to hashable strings first
            edges_gdf["name_hashable"] = edges_gdf["name"].apply(to_hashable)
            grouped = edges_gdf.groupby("name_hashable")
            for name, group in grouped:
                if name and str(name).strip():
                    road_groups[str(name)] = group
        
        # Also group by ref (for numbered roads like A487)
        if "ref" in edges_gdf.columns:
            # Convert to hashable strings first
            edges_gdf["ref_hashable"] = edges_gdf["ref"].apply(to_hashable)
            ref_grouped = edges_gdf.groupby("ref_hashable")
            for ref, group in ref_grouped:
                if ref and str(ref).strip():
                    ref_name = str(ref)
                    if ref_name not in road_groups:
                        road_groups[ref_name] = group
        
        return road_groups
    
    async def _create_road_with_segments(
        self,
        edges: gpd.GeoDataFrame,
        road_data: Dict[str, Any]
    ) -> Road:
        """Create a new road record with all its segments."""
        from shapely.ops import unary_union
        
        # Create road record
        road_create = RoadCreate(
            name=road_data["name"],
            ref=road_data.get("ref"),
            road_type=road_data.get("road_type"),
            total_length_m=road_data["total_length_m"],
            segment_count=road_data["segment_count"],
            speed_limit=road_data.get("speed_limit"),
            surface_type=road_data.get("surface_type"),
            bbox=road_data.get("bbox"),
            center_lat=road_data.get("center_lat"),
            center_lon=road_data.get("center_lon")
        )
        
        road = self.road_service.create_road(road_create)
        
        # Create segments
        segment_details = self.osm_service.get_segment_details(edges)
        
        for seg_data in segment_details:
            # Helper to safely convert values
            import re
            def safe_str(val):
                if val is None or pd.isna(val):
                    return None
                if isinstance(val, (list, tuple)):
                    return str(val[0]) if len(val) > 0 else None
                if isinstance(val, np.ndarray):
                    return str(val.item()) if val.size == 1 else str(val[0]) if val.size > 0 else None
                return str(val)
            
            def safe_float(val):
                if val is None or pd.isna(val):
                    return None
                try:
                    if isinstance(val, str):
                        nums = re.findall(r'\d+\.?\d*', val)
                        return float(nums[0]) if nums else None
                    return float(val)
                except (ValueError, TypeError):
                    return None
            
            # Convert geometry to GeoAlchemy2 format for PostGIS
            geom = seg_data.get("geometry")
            if geom is not None:
                # Use from_shape to convert Shapely geometry to WKBElement
                from app.database.connection import engine
                geom_wkb = from_shape(geom, srid=4326)
            else:
                geom_wkb = None
            
            # Extract segment data with safe defaults
            segment_data = {
                "road_id": road.id,
                "osm_id": safe_str(seg_data["osm_id"]),
                "segment_length_m": safe_float(seg_data.get("length_m")) or 0.0,
                "road_type": safe_str(seg_data.get("road_type")),
                "maxspeed": safe_str(seg_data.get("maxspeed")),
                "surface": safe_str(seg_data.get("surface")),
                "lanes": safe_str(seg_data.get("lanes")),
                "width": safe_float(seg_data.get("width")),
                "osm_name": safe_str(seg_data.get("osm_name")),
                "osm_ref": safe_str(seg_data.get("osm_ref")),
                "geometry": geom_wkb,
                "start_lat": safe_float(seg_data.get("start_point", [None, None])[0]) or 0.0,
                "start_lon": safe_float(seg_data.get("start_point", [None, None])[1]) or 0.0,
                "end_lat": safe_float(seg_data.get("end_point", [None, None])[0]) or 0.0,
                "end_lon": safe_float(seg_data.get("end_point", [None, None])[1]) or 0.0,
                "osm_tags": seg_data.get("raw_tags", {})
            }
            
            segment = RoadSegment(**segment_data)
            self.db.add(segment)
        
        self.db.commit()
        
        # Perform analysis on segments (async)
        await self._analyze_road_segments(road.id)
        
        return road
    
    def _update_road_with_segments(
        self,
        road: Road,
        edges: gpd.GeoDataFrame,
        road_data: Dict[str, Any]
    ):
        """Update existing road with new segment data."""
        # Helper to convert numpy values to Python native types
        def to_python(val):
            if val is None:
                return None
            if isinstance(val, np.ndarray):
                return val.item() if val.size == 1 else float(val[0]) if val.size > 0 else None
            if isinstance(val, (np.integer, np.floating)):
                return val.item()
            return val
        
        # Update road properties
        road.total_length_m = to_python(road_data["total_length_m"])
        road.segment_count = to_python(road_data["segment_count"])
        road.speed_limit = road_data.get("speed_limit")
        road.surface_type = road_data.get("surface_type")
        
        if road_data.get("bbox"):
            road.bbox_west = to_python(road_data["bbox"]["west"])
            road.bbox_south = to_python(road_data["bbox"]["south"])
            road.bbox_east = to_python(road_data["bbox"]["east"])
            road.bbox_north = to_python(road_data["bbox"]["north"])
        
        # Note: We don't recreate segments for existing roads to avoid duplicates
        # In a real system, you might want to check for new/deleted segments
        
        self.db.commit()
    
    async def _analyze_road_segments(self, road_id: int):
        """Perform geometry and elevation analysis on road segments."""
        road = self.road_service.get_road(road_id)
        if not road or not road.segments:
            return
        
        for segment in road.segments:
            try:
                # Geometry analysis
                geom_analysis = self.geometry_service.analyze_segment(segment)
                
                # Estimate width
                estimated_width = self.geometry_service.estimate_width(segment)
                if estimated_width:
                    segment.width = estimated_width
                
                # Elevation analysis (if we have enough coordinate detail)
                # For now, we use start and end points
                if segment.start_lat and segment.end_lat:
                    coords = [
                        (segment.start_lat, segment.start_lon),
                        (segment.end_lat, segment.end_lon)
                    ]
                    
                    elev_analysis = await self.elevation_service.analyze_segment_elevation(
                        coords,
                        segment.segment_length_m
                    )
                    
                    # Combine analyses
                    combined_analysis = {
                        **geom_analysis,
                        **elev_analysis
                    }
                    
                    segment.analysis_data = combined_analysis
                
                self.db.commit()
                
            except Exception as e:
                print(f"Analysis error for segment {segment.id}: {e}")
    
    async def sync_single_road(self, road_name: str) -> Optional[Road]:
        """
        Sync a single road by name (for on-demand imports).
        """
        # Search in OSM
        edges = self.osm_service.search_roads(road_name, exact_match=False)
        
        if edges.empty:
            return None
        
        # Aggregate
        road_data = self.osm_service.aggregate_road_data(edges)
        
        if not road_data:
            return None
        
        # Check if exists
        existing = self.road_service.get_road_by_name(road_data["name"])
        if existing:
            self._update_road_with_segments(existing, edges, road_data)
            return existing
        
        # Create new
        return await self._create_road_with_segments(edges, road_data)
    
    async def refresh_road_analysis(self, road_id: int) -> Optional[Road]:
        """
        Re-run analysis on an existing road's segments.
        """
        road = self.road_service.get_road(road_id)
        if not road:
            return None
        
        await self._analyze_road_segments(road_id)
        
        return self.road_service.get_road(road_id)
    
    async def close(self):
        """Clean up resources."""
        await self.elevation_service.close()
