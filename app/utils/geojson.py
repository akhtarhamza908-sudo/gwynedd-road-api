"""
Helper functions for converting road and segment models to GeoJSON format.
"""
from typing import List, Dict, Any, Optional

from geoalchemy2.shape import to_shape
from shapely.geometry import mapping

from app.models.road import Road
from app.models.segment import RoadSegment


def _convert_to_json(obj: Any) -> Any:
    """Recursively convert tuples to JSON-serializable lists."""
    if isinstance(obj, tuple):
        return [_convert_to_json(item) for item in obj]
    if isinstance(obj, list):
        return [_convert_to_json(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _convert_to_json(v) for k, v in obj.items()}
    return obj


def road_to_geojson_feature(road: Road) -> Optional[Dict[str, Any]]:
    if not road:
        return None

    geometry = None
    if road.geometry is not None:
        try:
            geometry = _convert_to_json(mapping(to_shape(road.geometry)))
        except Exception as e:
            print(f"GeoJSON mapping error for road {road.id}: {e}")

    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "id": road.id,
            "name": road.name,
            "ref": road.ref,
            "road_type": road.road_type,
            "total_length_m": road.total_length_m,
            "segment_count": road.segment_count,
            "speed_limit": road.speed_limit,
            "surface_type": road.surface_type,
            "bbox": road.get_bbox_dict()
        }
    }


def segment_to_geojson_feature(segment: RoadSegment) -> Optional[Dict[str, Any]]:
    if not segment:
        return None

    geometry = None
    if segment.geometry is not None:
        try:
            geometry = _convert_to_json(mapping(to_shape(segment.geometry)))
        except Exception as e:
            print(f"GeoJSON mapping error for segment {segment.id}: {e}")

    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "id": segment.id,
            "road_id": segment.road_id,
            "osm_id": segment.osm_id,
            "segment_length_m": segment.segment_length_m,
            "road_type": segment.road_type,
            "maxspeed": segment.maxspeed,
            "surface": segment.surface,
            "lanes": segment.lanes,
            "width": segment.width
        }
    }


def build_feature_collection(
    features: List[Optional[Dict[str, Any]]],
    bbox: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [f for f in features if f is not None],
        "bbox": bbox
    }
