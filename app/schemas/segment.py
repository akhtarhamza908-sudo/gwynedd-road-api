"""
Pydantic schemas for RoadSegment entities.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field


class SegmentBase(BaseModel):
    """Base segment schema."""
    segment_length_m: float = Field(..., ge=0)
    road_type: Optional[str] = Field(None, max_length=50)
    maxspeed: Optional[str] = Field(None, max_length=50)
    surface: Optional[str] = Field(None, max_length=100)
    lanes: Optional[str] = Field(None, max_length=10)
    width: Optional[float] = Field(None, ge=0)


class SegmentCreate(SegmentBase):
    """Schema for creating a segment."""
    road_id: int
    osm_id: Optional[str] = Field(None, max_length=50)
    osm_name: Optional[str] = Field(None, max_length=255)
    osm_ref: Optional[str] = Field(None, max_length=50)
    start_lat: float = Field(..., ge=-90, le=90)
    start_lon: float = Field(..., ge=-180, le=180)
    end_lat: float = Field(..., ge=-90, le=90)
    end_lon: float = Field(..., ge=-180, le=180)
    geometry_wkt: Optional[str] = None  # Well-Known Text for geometry
    osm_tags: Optional[Dict[str, Any]] = None


class SegmentResponse(SegmentBase):
    """Schema for segment response."""
    id: int
    road_id: int
    osm_id: Optional[str] = None
    osm_name: Optional[str] = None
    osm_ref: Optional[str] = None
    start_point: List[float] = Field(..., description="[latitude, longitude]")
    end_point: List[float] = Field(..., description="[latitude, longitude]")
    created_at: datetime
    
    model_config = {"from_attributes": True}


class SegmentWithAnalysis(SegmentResponse):
    """Segment with detailed analysis data."""
    analysis: Optional[Dict[str, Any]] = None
    elevation_data: Optional[Dict[str, Any]] = None
