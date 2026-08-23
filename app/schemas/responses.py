"""
Common response schemas and request models.
"""
from typing import List, Optional, Dict, Any, TypeVar, Generic
from pydantic import BaseModel, Field


class HealthCheck(BaseModel):
    """Health check response."""
    status: str = "ok" #initialization 
    version: str #declaration
    database: str = "connected"
    cache: str = "connected"
    roads_loaded: int
    timestamp: str


class APIError(BaseModel):
    """Error response schema."""
    error: str
    message: str
    code: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


class SearchQuery(BaseModel):
    """Search query parameters."""
    query: str = Field(..., min_length=1, max_length=255, description="Search query string")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum number of results")
    offset: int = Field(default=0, ge=0, description="Number of results to skip")
    include_segments: bool = Field(default=False, description="Include segment details")
# http://localhost:8000/analysis/road

class PaginationParams(BaseModel):
    """Common pagination parameters."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_prev: bool


class RoadNotFoundError(BaseModel):
    """Error response for road not found."""
    error: str = "Road not found"
    road_name: str
    suggestions: Optional[List[str]] = None


class ValidationError(BaseModel):
    """Validation error details."""
    field: str
    message: str
    value: Optional[Any] = None


class ValidationErrorResponse(BaseModel):
    """Response for validation errors."""
    error: str = "Validation error"
    code: int = 400
    errors: List[ValidationError]
