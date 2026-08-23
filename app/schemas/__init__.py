"""
Pydantic schemas package for request/response validation.
"""
from app.schemas.road import (
    RoadBase,
    RoadCreate,
    RoadUpdate,
    RoadInDB,
    RoadResponse,
    RoadListResponse,
    RoadSearchResult,
    BoundingBox,
    RoadAnalysis,
    RoadWithSegments
)
from app.schemas.segment import (
    SegmentBase,
    SegmentCreate,
    SegmentResponse,
    SegmentWithAnalysis
)
from app.schemas.responses import (
    PaginatedResponse,
    SearchQuery,
    APIError,
    HealthCheck
)

__all__ = [
    "RoadBase", "RoadCreate", "RoadUpdate", "RoadInDB",
    "RoadResponse", "RoadListResponse", "RoadSearchResult",
    "BoundingBox", "RoadAnalysis", "RoadWithSegments",
    "SegmentBase", "SegmentCreate", "SegmentResponse", "SegmentWithAnalysis",
    "PaginatedResponse", "SearchQuery", "APIError", "HealthCheck"
]
