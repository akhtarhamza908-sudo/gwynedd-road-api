"""
Analysis endpoints for individual road segments.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.segment import RoadSegment
from app.services.geometry_service import GeometryAnalysisService

router = APIRouter(prefix="/roads", tags=["Analysis"])


@router.get("/{road_id}/segments/{seg_id}/analysis")
def get_segment_analysis(
    road_id: int,
    seg_id: int,
    db: Session = Depends(get_db)
):
    """
    Get geometry analysis for a specific segment of a road.
    """
    segment = (
        db.query(RoadSegment)
        .filter(RoadSegment.id == seg_id, RoadSegment.road_id == road_id)
        .first()
    )

    if not segment:
        raise HTTPException(
            status_code=404,
            detail=f"Segment {seg_id} not found for road {road_id}"
        )

    service = GeometryAnalysisService()
    analysis = service.analyze_segment(segment)

    return {
        "segment_id": seg_id,
        "road_id": road_id,
        "osm_id": segment.osm_id,
        "segment_length_m": segment.segment_length_m,
        "analysis": analysis
    }
