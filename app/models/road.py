"""
Road database model with PostGIS support.
"""
from typing import List, Optional
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Column, Integer, String, Float, DateTime, Index, func
from sqlalchemy.orm import relationship, Mapped

from app.database.connection import Base

#object relational Mapper(ORM)
class Road(Base):
    """
    Road entity representing a complete road with multiple segments.
    Stores aggregated information and bounding box.
    """
    __tablename__ = "roads"#immutable variable
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    ref = Column(String(50), nullable=True, index=True)  # Reference like A487
    road_type = Column(String(50), nullable=True)  # highway type
    total_length_m = Column(Float, nullable=False, default=0.0)
    segment_count = Column(Integer, default=0)
    
    # Speed and surface (aggregated from segments)
    speed_limit = Column(String(50), nullable=True)
    surface_type = Column(String(100), nullable=True)
    
    # Bounding box as GeoJSON-like string or PostGIS geometry
    bbox_west = Column(Float, nullable=True)
    bbox_south = Column(Float, nullable=True)
    bbox_east = Column(Float, nullable=True)
    bbox_north = Column(Float, nullable=True)
    
    # Center point for spatial queries
    center_lat = Column(Float, nullable=True)
    center_lon = Column(Float, nullable=True)
    
    # Full geometry (LineString Multi for the entire road)
    geometry = Column(Geometry('MULTILINESTRING', srid=4326), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    segments: Mapped[List["RoadSegment"]] = relationship(
        "RoadSegment",
        back_populates="road",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<Road(id={self.id}, name='{self.name}', type='{self.road_type}')>"
    
    def get_bbox_dict(self) -> Optional[dict]:
        """Return bounding box as dictionary."""
        if all(v is not None for v in [self.bbox_west, self.bbox_south, self.bbox_east, self.bbox_north]):
            return {
                "west": self.bbox_west,
                "south": self.bbox_south,
                "east": self.bbox_east,
                "north": self.bbox_north
            }#json syntax
        return None


