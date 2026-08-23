"""
Road service for database operations and business logic.
"""
import re
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_, text
from geoalchemy2.functions import ST_AsGeoJSON, ST_Extent, ST_Centroid
import json

from app.models.road import Road
from app.models.segment import RoadSegment
from app.schemas.road import RoadCreate, RoadUpdate, RoadSearchResult
from app.schemas.segment import SegmentCreate
from app.utils.cache import get_cache


class RoadService:
    """
    Service for road-related database operations and business logic.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.cache = get_cache()
    
    # ==================== CRUD Operations ====================
    
    def create_road(self, road_data: RoadCreate) -> Road:
        """Create a new road record."""
        db_road = Road(
            name=road_data.name,
            ref=road_data.ref,
            road_type=road_data.road_type,
            total_length_m=road_data.total_length_m,
            segment_count=road_data.segment_count,
            speed_limit=road_data.speed_limit,
            surface_type=road_data.surface_type,
            bbox_west=road_data.bbox.west if road_data.bbox else None,
            bbox_south=road_data.bbox.south if road_data.bbox else None,
            bbox_east=road_data.bbox.east if road_data.bbox else None,
            bbox_north=road_data.bbox.north if road_data.bbox else None,
            center_lat=road_data.center_lat,
            center_lon=road_data.center_lon
        )
        
        self.db.add(db_road)
        self.db.commit()
        self.db.refresh(db_road)
        
        # Invalidate cache
        self._invalidate_search_cache()
        
        return db_road
    
    def get_road(self, road_id: int) -> Optional[Road]:
        """Get road by ID with segments loaded."""
        cache_key = f"road:{road_id}"
        cached = self.cache.get(cache_key)
        
        if cached:
            return cached
        
        road = self.db.query(Road).options(
            joinedload(Road.segments)
        ).filter(Road.id == road_id).first()
        
        if road:
            self.cache.set(cache_key, road, ttl=300)  # Cache for 5 minutes
        
        return road
    
    def get_road_by_name(self, name: str) -> Optional[Road]:
        """Get road by exact name match."""
        # Ensure name is a string
        if isinstance(name, list):
            name = str(name[0]) if name else ""
        name_str = str(name) if name else ""
        return self.db.query(Road).filter(
            func.lower(Road.name) == name_str.lower()
        ).first()
    
    def search_roads(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Road], int]:
        """
        Smart search for roads with partial matching.
        
        Returns:
            Tuple of (roads list, total count)
        """
        cache_key = f"search:{query.lower()}:{limit}:{offset}"
        cached = self.cache.get(cache_key)
        
        if cached:
            return cached
        
        # Normalize query
        search_term = f"%{query.lower()}%"
        
        # Build query with name and ref search
        base_query = self.db.query(Road).filter(
            or_(
                func.lower(Road.name).like(search_term),
                func.lower(Road.ref).like(search_term)
            )
        )
        
        # Get total count
        total = base_query.count()
        
        # Get paginated results
        roads = base_query.order_by(
            func.length(Road.name)  # Shorter names first (exact matches tend to be shorter)
        ).offset(offset).limit(limit).all()
        
        result = (roads, total)
        self.cache.set(cache_key, result, ttl=600)  # Cache for 10 minutes
        
        return result
    
    def list_roads(
        self,
        page: int = 1,
        page_size: int = 20,
        road_type: Optional[str] = None
    ) -> Tuple[List[Road], int]:
        """
        List all roads with optional filtering.
        
        Returns:
            Tuple of (roads list, total count)
        """
        query = self.db.query(Road)
        
        if road_type:
            query = query.filter(Road.road_type == road_type)
        
        total = query.count()
        
        roads = query.order_by(Road.name).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        return roads, total
    
    def update_road(self, road_id: int, road_update: RoadUpdate) -> Optional[Road]:
        """Update road record."""
        road = self.get_road(road_id)
        if not road:
            return None
        
        update_data = road_update.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(road, field, value)
        
        self.db.commit()
        self.db.refresh(road)
        
        # Invalidate caches
        self.cache.delete(f"road:{road_id}")
        self._invalidate_search_cache()
        
        return road
    
    def delete_road(self, road_id: int) -> bool:
        """Delete road and its segments."""
        road = self.get_road(road_id)
        if not road:
            return False
        
        self.db.delete(road)
        self.db.commit()
        
        # Invalidate caches
        self.cache.delete(f"road:{road_id}")
        self._invalidate_search_cache()
        
        return True
    
    # ==================== Segment Operations ====================
    
    def create_segment(self, road_id: int, segment_data: SegmentCreate) -> RoadSegment:
        """Create a new road segment."""
        from geoalchemy2.shape import from_shape
        from shapely.geometry import LineString
        
        # Create geometry from coordinates
        geom = LineString([
            (segment_data.start_lon, segment_data.start_lat),
            (segment_data.end_lon, segment_data.end_lat)
        ])
        
        db_segment = RoadSegment(
            road_id=road_id,
            osm_id=segment_data.osm_id,
            segment_length_m=segment_data.segment_length_m,
            road_type=segment_data.road_type,
            maxspeed=segment_data.maxspeed,
            surface=segment_data.surface,
            lanes=segment_data.lanes,
            width=segment_data.width,
            osm_name=segment_data.osm_name,
            osm_ref=segment_data.osm_ref,
            start_lat=segment_data.start_lat,
            start_lon=segment_data.start_lon,
            end_lat=segment_data.end_lat,
            end_lon=segment_data.end_lon,
            geometry=from_shape(geom, srid=4326),
            osm_tags=segment_data.osm_tags
        )
        
        self.db.add(db_segment)
        self.db.commit()
        self.db.refresh(db_segment)
        
        return db_segment
    
    def get_segment(self, segment_id: int) -> Optional[RoadSegment]:
        """Get segment by ID."""
        return self.db.query(RoadSegment).filter(RoadSegment.id == segment_id).first()
    
    def update_segment_analysis(
        self,
        segment_id: int,
        analysis_data: Dict[str, Any]
    ) -> Optional[RoadSegment]:
        """Update segment analysis data."""
        segment = self.get_segment(segment_id)
        if not segment:
            return None
        
        segment.analysis_data = analysis_data
        self.db.commit()
        self.db.refresh(segment)
        
        return segment
    
    # ==================== Spatial Queries ====================
    
    def get_roads_in_bbox(
        self,
        west: float,
        south: float,
        east: float,
        north: float
    ) -> List[Road]:
        """Find roads within bounding box."""
        # Build bbox polygon
        bbox_wkt = f"POLYGON(({west} {south}, {east} {south}, {east} {north}, {west} {north}, {west} {south}))"
        
        query = text("""
            SELECT r.* FROM roads r
            WHERE ST_Intersects(
                r.geometry,
                ST_GeomFromText(:bbox, 4326)
            )
            ORDER BY r.name
        """)
        
        result = self.db.execute(query, {"bbox": bbox_wkt})
        return result.mappings().all()
    
    def get_road_bbox(self, road_id: int) -> Optional[Dict[str, float]]:
        """Get bounding box for a specific road."""
        road = self.get_road(road_id)
        if not road:
            return None
        
        return road.get_bbox_dict()
    
    # ==================== Helper Methods ====================
    
    def _invalidate_search_cache(self):
        """Invalidate all search-related cache entries."""
        self.cache.clear()  # Simple approach: clear all cache
    
    def calculate_match_score(self, road: Road, query: str) -> float:
        """
        Calculate relevance score for search result ordering.
        Higher score = better match.
        """
        query_lower = query.lower()
        # Ensure road.name is a string
        road_name = road.name
        if isinstance(road_name, list):
            road_name = str(road_name[0]) if road_name else ""
        name_lower = str(road_name).lower() if road_name else ""
        
        score = 0.0
        
        # Exact match gets highest score
        if name_lower == query_lower:
            score += 100
        # Starts with query
        elif name_lower.startswith(query_lower):
            score += 50
        # Contains query
        elif query_lower in name_lower:
            score += 25
        
        # Ref match bonus
        road_ref = road.ref
        if isinstance(road_ref, list):
            road_ref = str(road_ref[0]) if road_ref else None
        if road_ref and query_lower in str(road_ref).lower():
            score += 30
        
        # Shorter names get slight preference
        score += max(0, 20 - len(name_lower) / 10)
        
        return score
    
    def road_to_dict(self, road: Road, include_segments: bool = False) -> Dict[str, Any]:
        """Convert Road model to dictionary."""
        # Get start and end points from segments
        start_point = None
        end_point = None
        
        if road.segments:
            # Get first segment's start point
            first_seg = road.segments[0]
            if first_seg.start_lat is not None and first_seg.start_lon is not None:
                start_point = [first_seg.start_lat, first_seg.start_lon]
            
            # Get last segment's end point
            last_seg = road.segments[-1]
            if last_seg.end_lat is not None and last_seg.end_lon is not None:
                end_point = [last_seg.end_lat, last_seg.end_lon]
        
        data = {
            "id": road.id,
            "name": road.name,
            "ref": road.ref,
            "road_type": road.road_type,
            "total_length_m": road.total_length_m,
            "segment_count": road.segment_count,
            "speed_limit": road.speed_limit,
            "surface_type": road.surface_type,
            "start_point": start_point,
            "end_point": end_point,
            "bbox": road.get_bbox_dict(),
            "center_lat": road.center_lat,
            "center_lon": road.center_lon,
            "created_at": road.created_at.isoformat() if road.created_at else None,
            "updated_at": road.updated_at.isoformat() if road.updated_at else None
        }
        
        if include_segments and road.segments:
            data["segments"] = [
                {
                    "id": seg.id,
                    "length_m": seg.segment_length_m,
                    "road_type": seg.road_type,
                    "start_lat": seg.start_lat,
                    "start_lon": seg.start_lon,
                    "end_lat": seg.end_lat,
                    "end_lon": seg.end_lon
                }
                for seg in road.segments
            ]
        
        return data
