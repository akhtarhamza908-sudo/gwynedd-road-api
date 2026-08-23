"""
Pydantic schemas for Road entities.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class BoundingBox(BaseModel):
    """Bounding box coordinates."""
    west: float = Field(..., description="Western boundary (min longitude)")
    south: float = Field(..., description="Southern boundary (min latitude)")
    east: float = Field(..., description="Eastern boundary (max longitude)")
    north: float = Field(..., description="Northern boundary (max latitude)")


class RoadAnalysis(BaseModel):
    """Road geometry analysis results."""
    curvature: Optional[float] = Field(None, description="Average curvature index")
    turn_count: Optional[int] = Field(None, description="Number of significant turns")
    elevation_gain: Optional[float] = Field(None, description="Total elevation gain in meters")
    elevation_loss: Optional[float] = Field(None, description="Total elevation loss in meters")
    max_slope: Optional[float] = Field(None, description="Maximum slope percentage")
    avg_slope: Optional[float] = Field(None, description="Average slope percentage")
    estimated_width: Optional[float] = Field(None, description="Estimated road width in meters")


class RoadBase(BaseModel):
    """Base road schema with common fields."""
    name: str = Field(..., min_length=2, max_length=255, description="Road name")
    ref: Optional[str] = Field(None, max_length=50, description="Road reference code (e.g., A487)")
    road_type: Optional[str] = Field(None, max_length=50, description="Highway classification")
    speed_limit: Optional[str] = Field(None, max_length=50, description="Speed limit")
    surface_type: Optional[str] = Field(None, max_length=100, description="Surface material")


class RoadCreate(RoadBase):
    """Schema for creating a new road record."""
    total_length_m: float = Field(..., ge=0, description="Total length in meters")
    segment_count: int = Field(default=0, ge=0)
    bbox: Optional[BoundingBox] = None
    center_lat: Optional[float] = None
    center_lon: Optional[float] = None


class RoadUpdate(BaseModel):
    """Schema for updating road record."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    ref: Optional[str] = Field(None, max_length=50)
    road_type: Optional[str] = None
    speed_limit: Optional[str] = None
    surface_type: Optional[str] = None
    total_length_m: Optional[float] = Field(None, ge=0)
    segment_count: Optional[int] = Field(None, ge=0)


class RoadInDB(RoadBase):
    """Schema representing road as stored in database."""
    id: int
    total_length_m: float
    segment_count: int
    bbox_west: Optional[float] = None
    bbox_south: Optional[float] = None
    bbox_east: Optional[float] = None
    bbox_north: Optional[float] = None
    center_lat: Optional[float] = None
    center_lon: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RoadSegmentSummary(BaseModel):
    """Summary of a road segment."""
    id: int
    segment_length_m: float
    road_type: Optional[str] = None
    start_point: List[float]
    end_point: List[float]


class RoadResponse(RoadBase):
    """Schema for road API response."""
    id: int
    total_length_m: float
    segment_count: int
    start_point: Optional[List[float]] = Field(None, description="[latitude, longitude]")
    end_point: Optional[List[float]] = Field(None, description="[latitude, longitude]")
    bbox: Optional[BoundingBox] = None
    analysis: Optional[RoadAnalysis] = None
    
    model_config = {"from_attributes": True}


class RoadWithSegments(RoadResponse):
    """Road response including segment details."""
    segments: List[RoadSegmentSummary]


class RoadListResponse(BaseModel):
    """Response for listing multiple roads."""
    roads: List[RoadResponse]
    total: int
    page: int
    page_size: int
    pages: int


class RoadSearchResult(BaseModel):
    """Single search result for road search endpoint."""
    id: int
    name: str
    ref: Optional[str] = None
    road_type: Optional[str] = None
    total_length_m: float
    match_score: float = Field(..., description="Search relevance score")
    center_point: Optional[List[float]] = None

#geo:earth
#json: javascript object notation
#geometry: geometric shapes/structures
class GeoJSONGeometry(BaseModel):
    """GeoJSON geometry object."""
    type: str = "MultiLineString"
    coordinates: List[List[List[float]]]  # MultiLineString format
# [1,[1,[2,56],2,3],3,4,5,6,7,8,9,10]

class GeoJSONProperties(BaseModel):
    """GeoJSON properties object."""
    id: int
    name: str
    ref: Optional[str] = None
    road_type: Optional[str] = None
    total_length_m: float
    segment_count: int
    speed_limit: Optional[str] = None
    surface_type: Optional[str] = None


class GeoJSONFeature(BaseModel):
    """GeoJSON Feature object."""
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: GeoJSONProperties


class GeoJSONFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection object."""
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]
    bbox: Optional[BoundingBox] = None
