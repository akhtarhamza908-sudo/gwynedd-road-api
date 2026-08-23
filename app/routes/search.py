"""
Search endpoints: smart search, autocomplete suggestions, and nearby roads.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.database.connection import get_db
from app.models.road import Road
from app.schemas.road import RoadSearchResult
from app.services.road_service import RoadService

router = APIRouter(prefix="/roads", tags=["Search"])


@router.get("/search")
def search_roads(
    query: str = Query(..., min_length=1, max_length=255, description="Search term"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    include_segments: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Smart search for roads by name or reference number.
    Supports partial matches (e.g., 'High' matches 'High Street').
    """
    service = RoadService(db)
    roads, total = service.search_roads(query, limit=limit, offset=offset)

    results = []
    for road in roads:
        score = service.calculate_match_score(road, query)
        center_point = None
        if road.center_lat is not None and road.center_lon is not None:
            center_point = [road.center_lat, road.center_lon]

        results.append(RoadSearchResult(
            id=road.id,
            name=road.name,
            ref=road.ref,
            road_type=road.road_type,
            total_length_m=road.total_length_m,
            match_score=score,
            center_point=center_point
        ))

    return {
        "query": query,
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": results
    }


@router.get("/search/suggestions")
def search_suggestions(
    query: str = Query(..., min_length=1, max_length=255),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Autocomplete suggestions for road names and references."""
    service = RoadService(db)
    roads, _ = service.search_roads(query, limit=limit, offset=0)
    suggestions = [r.name for r in roads if r.name]
    return {"query": query, "suggestions": suggestions}


@router.get("/nearby")
def nearby_roads(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius: float = Query(1000, ge=1, description="Radius in meters"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Find roads near a given GPS coordinate.

    Uses a simple bounding-box approximation around the point, then filters by
    straight-line distance. This avoids requiring a full PostGIS installation
    check on every request.
    """
    import math

    # Approximate degrees per meter
    lat_delta = radius / 111320.0
    lon_delta = radius / (111320.0 * math.cos(math.radians(lat)))

    min_lat = lat - lat_delta
    max_lat = lat + lat_delta
    min_lon = lon - lon_delta
    max_lon = lon + lon_delta

    roads = (
        db.query(Road)
        .filter(
            Road.center_lat.between(min_lat, max_lat),
            Road.center_lon.between(min_lon, max_lon)
        )
        .all()
    )

    def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371000  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    results = []
    for road in roads:
        if road.center_lat is None or road.center_lon is None:
            continue
        distance = haversine(lat, lon, road.center_lat, road.center_lon)
        if distance <= radius:
            results.append({
                "id": road.id,
                "name": road.name,
                "ref": road.ref,
                "road_type": road.road_type,
                "distance_m": round(distance, 2),
                "center_point": [road.center_lat, road.center_lon]
            })

    results.sort(key=lambda x: x["distance_m"])
    return {
        "lat": lat,
        "lon": lon,
        "radius_m": radius,
        "count": len(results),
        "roads": results[:limit]
    }
