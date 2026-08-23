"""
Road segment database model representing individual OSM road segments.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship, Mapped

from app.database.connection import Base


class RoadSegment(Base):
    """
    Individual road segment from OpenStreetMap.
    Multiple segments can belong to one Road entity.
    """
    __tablename__ = "road_segments"
    
    id = Column(Integer, primary_key=True, index=True)
    road_id = Column(Integer, ForeignKey("roads.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Original OSM ID
    osm_id = Column(String(50), nullable=True, index=True)
    
    # Segment attributes from OSM
    segment_length_m = Column(Float, nullable=False)
    road_type = Column(String(50), nullable=True)  # highway tag
    maxspeed = Column(String(50), nullable=True)   # speed limit
    surface = Column(String(100), nullable=True)   # surface type
    lanes = Column(String(10), nullable=True)      # number of lanes
    width = Column(Float, nullable=True)           # width in meters
    
    # Original OSM name (may differ from aggregated road name)
    osm_name = Column(String(255), nullable=True)
    osm_ref = Column(String(50), nullable=True)
    
    # Geometry (LineString for this segment)
    geometry = Column(Geometry('LINESTRING', srid=4326), nullable=False)
    
    # Start and end coordinates
    start_lat = Column(Float, nullable=False)
    start_lon = Column(Float, nullable=False)
    end_lat = Column(Float, nullable=False)
    end_lon = Column(Float, nullable=False)
    
    # Analysis data (stored as JSON for flexibility)
    analysis_data = Column(JSON, nullable=True)
    # Example structure:
    # {
    #   "curvature": 0.15,
    #   "turn_count": 5,
    #   "elevation_gain": 45.2,
    #   "elevation_loss": 30.1,
    #   "max_slope": 8.5,
    #   "avg_slope": 3.2
    # }
    
    # Raw OSM tags for reference
    osm_tags = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    road: Mapped["Road"] = relationship("Road", back_populates="segments")
    
    def __repr__(self) -> str:
        return f"<RoadSegment(id={self.id}, road_id={self.road_id}, length={self.segment_length_m}m)>"
    
    def get_start_point(self) -> List[float]:
        """Return start point as [lat, lon]."""
        return [self.start_lat, self.start_lon]
    
    def get_end_point(self) -> List[float]:
        """Return end point as [lat, lon]."""
        return [self.end_lat, self.end_lon]
    
    def get_analysis(self) -> Dict[str, Any]:
        """Return analysis data as dictionary."""
        return self.analysis_data or {}


