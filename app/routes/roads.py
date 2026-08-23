"""
Road endpoints: CRUD, GeoJSON export, analysis, and elevation profiles.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.connection import get_db
from app.models.road import Road
from app.models.segment import RoadSegment
from app.schemas.road import (
    RoadListResponse,
    RoadResponse,
    RoadWithSegments,
    GeoJSONFeatureCollection,
    BoundingBox,
    RoadAnalysis
)
from app.services.road_service import RoadService
from app.services.sync_service import DataSyncService
from app.utils.geojson import road_to_geojson_feature, segment_to_geojson_feature, build_feature_collection

router = APIRouter(prefix="/roads", tags=["Roads"])


def _get_road_service(db: Session = Depends(get_db)) -> RoadService:
    return RoadService(db)


@router.get("/", response_model=RoadListResponse)
def list_roads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    road_type: Optional[str] = Query(None, description="Filter by road type (highway classification)"),
    db: Session = Depends(get_db)
):
    """List all roads in the database with pagination and optional type filter."""
    service = RoadService(db)
    roads, total = service.list_roads(page=page, page_size=page_size, road_type=road_type)
    pages = (total + page_size - 1) // page_size if page_size > 0 else 1

    return RoadListResponse(
        roads=[RoadResponse.model_validate(service.road_to_dict(r)) for r in roads],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/statistics")
def get_statistics(db: Session = Depends(get_db)):
    """Return high-level statistics about the road network."""
    road_count = db.query(Road).count()
    segment_count = db.query(RoadSegment).count()
    total_length = db.query(func.sum(Road.total_length_m)).scalar() or 0.0

    type_counts = (
        db.query(Road.road_type, func.count(Road.id))
        .filter(Road.road_type.isnot(None))
        .group_by(Road.road_type)
        .all()
    )

    return {
        "road_count": road_count,
        "segment_count": segment_count,
        "total_length_m": round(float(total_length), 2),
        "total_length_km": round(float(total_length) / 1000, 2),
        "road_type_counts": {t or "unknown": c for t, c in type_counts}
    }


@router.get("/by-name/{name}", response_model=RoadResponse)
def get_road_by_name(
    name: str,
    service: RoadService = Depends(_get_road_service)
):
    """Get a single road by exact name (case-insensitive)."""
    road = service.get_road_by_name(name)
    if not road:
        raise HTTPException(status_code=404, detail=f"Road '{name}' not found")
    return RoadResponse.model_validate(service.road_to_dict(road))


@router.get("/{road_id}", response_model=RoadResponse)
def get_road(
    road_id: int,
    include_segments: bool = Query(False, description="Include segment details"),
    service: RoadService = Depends(_get_road_service)
):
    """Get a road by its database ID."""
    road = service.get_road(road_id)
    if not road:
        raise HTTPException(status_code=404, detail=f"Road with id {road_id} not found")

    data = service.road_to_dict(road, include_segments=include_segments)
    if include_segments:
        return RoadWithSegments.model_validate(data)
    return RoadResponse.model_validate(data)


@router.get("/{road_id}/segments")
def get_road_segments(
    road_id: int,
    service: RoadService = Depends(_get_road_service)
):
    """Get all segments belonging to a specific road."""
    road = service.get_road(road_id)
    if not road:
        raise HTTPException(status_code=404, detail=f"Road with id {road_id} not found")

    segments_data = []
    for segment in road.segments:
        segments_data.append({
            "id": segment.id,
            "osm_id": segment.osm_id,
            "segment_length_m": segment.segment_length_m,
            "road_type": segment.road_type,
            "maxspeed": segment.maxspeed,
            "surface": segment.surface,
            "lanes": segment.lanes,
            "width": segment.width,
            "start_point": segment.get_start_point(),
            "end_point": segment.get_end_point(),
            "analysis_data": segment.get_analysis()
        })

    return {
        "road_id": road_id,
        "road_name": road.name,
        "segment_count": len(segments_data),
        "segments": segments_data
    }


@router.get("/{road_id}/bbox", response_model=BoundingBox)
def get_road_bbox(
    road_id: int,
    service: RoadService = Depends(_get_road_service)
):
    """Get the bounding box for a road."""
    bbox = service.get_road_bbox(road_id)
    if not bbox:
        raise HTTPException(status_code=404, detail=f"Road with id {road_id} not found")
    return BoundingBox(**bbox)


@router.get("/{road_id}/geojson")
def get_road_geojson(
    road_id: int,
    service: RoadService = Depends(_get_road_service)
):
    """Export a road and its segments as a GeoJSON FeatureCollection."""
    road = service.get_road(road_id)
    if not road:
        raise HTTPException(status_code=404, detail=f"Road with id {road_id} not found")

    features = [road_to_geojson_feature(road)]
    for segment in road.segments:
        features.append(segment_to_geojson_feature(segment))

    bbox = road.get_bbox_dict()
    return build_feature_collection(features, bbox=bbox)


@router.get("/{road_id}/analysis", response_model=RoadAnalysis)
def get_road_analysis(
    road_id: int,
    service: RoadService = Depends(_get_road_service)
):
    """Get aggregated geometry analysis for a road."""
    road = service.get_road(road_id)
    if not road:
        raise HTTPException(status_code=404, detail=f"Road with id {road_id} not found")

    if not road.segments:
        return RoadAnalysis()

    total_turns = 0
    total_curvature = 0.0
    total_sinuosity = 0.0
    total_gain = 0.0
    total_loss = 0.0
    max_slope = 0.0
    avg_slopes = []
    width_values = []
    analyzed_count = 0

    for segment in road.segments:
        analysis = segment.get_analysis() or {}
        if not analysis:
            continue

        analyzed_count += 1
        total_turns += analysis.get("turn_count", 0) or 0
        total_curvature += analysis.get("curvature", 0.0) or 0.0
        total_sinuosity += analysis.get("sinuosity", 1.0) or 1.0
        total_gain += analysis.get("elevation_gain", 0.0) or 0.0
        total_loss += analysis.get("elevation_loss", 0.0) or 0.0

        seg_max_slope = analysis.get("max_slope", 0.0) or 0.0
        if seg_max_slope > max_slope:
            max_slope = seg_max_slope

        seg_avg_slope = analysis.get("avg_slope", 0.0) or 0.0
        if seg_avg_slope:
            avg_slopes.append(seg_avg_slope)

        if segment.width:
            width_values.append(segment.width)

    if analyzed_count == 0:
        return RoadAnalysis()

    estimated_width = sum(width_values) / len(width_values) if width_values else None

    return RoadAnalysis(
        curvature=round(total_curvature / analyzed_count, 4),
        turn_count=total_turns,
        elevation_gain=round(total_gain, 2),
        elevation_loss=round(total_loss, 2),
        max_slope=round(max_slope, 2),
        avg_slope=round(sum(avg_slopes) / len(avg_slopes), 2) if avg_slopes else 0.0,
        estimated_width=round(estimated_width, 2) if estimated_width else None
    )


@router.get("/{road_id}/elevation-profile")
def get_elevation_profile(
    road_id: int,
    service: RoadService = Depends(_get_road_service)
):
    """Get the combined elevation profile for a road."""
    road = service.get_road(road_id)
    if not road:
        raise HTTPException(status_code=404, detail=f"Road with id {road_id} not found")

    profile = {
        "road_id": road_id,
        "road_name": road.name,
        "total_elevation_gain": 0.0,
        "total_elevation_loss": 0.0,
        "max_slope": 0.0,
        "avg_slope": 0.0,
        "segments": []
    }

    avg_slopes = []
    for segment in road.segments:
        analysis = segment.get_analysis() or {}
        seg_profile = {
            "segment_id": segment.id,
            "length_m": segment.segment_length_m,
            "start_elevation": analysis.get("start_elevation"),
            "end_elevation": analysis.get("end_elevation"),
            "elevation_gain": analysis.get("elevation_gain", 0.0),
            "elevation_loss": analysis.get("elevation_loss", 0.0),
            "max_slope": analysis.get("max_slope", 0.0),
            "avg_slope": analysis.get("avg_slope", 0.0)
        }
        profile["segments"].append(seg_profile)
        profile["total_elevation_gain"] += seg_profile["elevation_gain"] or 0.0
        profile["total_elevation_loss"] += seg_profile["elevation_loss"] or 0.0

        seg_max = seg_profile["max_slope"] or 0.0
        if seg_max > profile["max_slope"]:
            profile["max_slope"] = seg_max

        seg_avg = seg_profile["avg_slope"] or 0.0
        if seg_avg:
            avg_slopes.append(seg_avg)

    profile["avg_slope"] = round(sum(avg_slopes) / len(avg_slopes), 2) if avg_slopes else 0.0
    profile["max_slope"] = round(profile["max_slope"], 2)
    profile["total_elevation_gain"] = round(profile["total_elevation_gain"], 2)
    profile["total_elevation_loss"] = round(profile["total_elevation_loss"], 2)

    return profile


@router.post("/{road_id}/analyze", response_model=RoadResponse)
async def analyze_road(
    road_id: int,
    db: Session = Depends(get_db)
):
    """Re-run geometry and elevation analysis on a single road."""
    sync_service = DataSyncService(db)
    try:
        road = await sync_service.refresh_road_analysis(road_id)
    finally:
        await sync_service.close()

    if not road:
        raise HTTPException(status_code=404, detail=f"Road with id {road_id} not found")

    road_service = RoadService(db)
    return RoadResponse.model_validate(road_service.road_to_dict(road))
