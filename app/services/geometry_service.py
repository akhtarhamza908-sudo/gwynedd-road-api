"""
Geometry analysis service for road segment analysis.
Calculates curvature, turns, and other geometric properties.
"""
import math
from typing import List, Tuple, Dict, Any, Optional
import numpy as np#nickname for numpy to avoid conflicts with math module
from shapely.geometry import LineString, Point
from shapely.ops import substring
from geoalchemy2.shape import to_shape

from app.models.segment import RoadSegment


class GeometryAnalysisService:
    """
    Service for analyzing road geometry and calculating metrics.
    """
    
    def __init__(self):
        self.min_turn_angle = 15  # Minimum angle to count as a turn (degrees)
        self.curvature_sample_distance = 50  # Sample every 50m for curvature
    
    def analyze_segment(
        self,
        segment: RoadSegment
    ) -> Dict[str, Any]:
        """
        Perform full geometry analysis on a road segment.
        
        Returns dictionary with:
        - curvature: Average curvature index
        - turn_count: Number of significant turns
        - sinuosity: Ratio of actual length to straight-line distance#sine function of teh road
        """
        try:
            # Get geometry as shapely object
            geom = to_shape(segment.geometry) if segment.geometry else None
            if not geom:
                return self._empty_analysis()
            
            coords = list(geom.coords) #exmaple of coordinates [(lon, lat), (lon, lat), ...]
            if len(coords) < 2:
                return self._empty_analysis()
            #(lat, lon)---------------------------------------------------------------(lat, lon)#
            # Calculate metrics
            curvature = self._calculate_curvature(coords)
            turn_count = self._count_turns(coords)
            sinuosity = self._calculate_sinuosity(coords)
            
            return {
                "curvature": round(curvature, 4),#2.2246->2.225
                "turn_count": turn_count,
                "sinuosity": round(sinuosity, 4),#2.2246->2.225
                "bearing_changes": self._calculate_bearing_changes(coords),
                "avg_segment_length": self._calculate_avg_segment_length(coords),
                "coordinate_count": len(coords)
            }
            
        except Exception as e:
            print(f"Geometry analysis error: {e}")
            return self._empty_analysis()
    
    def _calculate_curvature(
        self,
        coords: List[Tuple[float, float]]
    ) -> float:#8.232989898
        """
        Calculate average curvature of the road segment.
        
        Uses the cumulative angle change normalized by segment length.
        """
        if len(coords) < 3:#Need at least 3 points to calculate curvature
            return 0.0
         #(lat, lon) single point----------------------------(lat, lon) single point----------------------------(lat, lon) single point#
        total_angle_change = 0.0
        segment_count = 0
        
        for i in range(1, len(coords) - 1):#Start from second point and end at second to last point to get three consecutive points
            # Get three consecutive points
            p1 = np.array(coords[i - 1])
            p2 = np.array(coords[i])
            p3 = np.array(coords[i + 1])
            
            # Calculate vectors
            v1 = p2 - p1
            v2 = p3 - p2
            
            # Calculate angle between vectors
            angle = self._angle_between_vectors(v1, v2)
            total_angle_change += angle
            segment_count += 1
        
        if segment_count == 0:
            return 0.0

        # Normalize by number of segments (higher value = more curved)
        avg_curvature = total_angle_change / segment_count
        
        # Scale to 0-1 range (typical values are 0-45 degrees)
        normalized_curvature = min(avg_curvature / 45.0, 1.0)#45 degrees is a very sharp turn, so we use it as a reference for maximum curvature
        
        return normalized_curvature
    
    def _count_turns(
        self,
        coords: List[Tuple[float, float]]
    ) -> int:
        """
        Count significant turns in the road segment.
        
        A turn is counted when the direction change exceeds min_turn_angle.
        """
        if len(coords) < 3:
            return 0
        
        turn_count = 0
        
        for i in range(1, len(coords) - 1):
            p1 = np.array(coords[i - 1])
            p2 = np.array(coords[i])
            p3 = np.array(coords[i + 1])
            
            v1 = p2 - p1
            v2 = p3 - p2
            
            angle = self._angle_between_vectors(v1, v2)
            
            if angle > self.min_turn_angle:
                turn_count += 1
        
        return turn_count
    
    def _calculate_sinuosity(
        self,
        coords: List[Tuple[float, float]]
    ) -> float:
        """
        Calculate sinuosity (meandering index).
        
        Ratio of actual path length to straight-line distance.
        1.0 = perfectly straight, higher = more winding.
        """
        if len(coords) < 2:
            return 1.0
        
        # Calculate actual path length
        actual_length = 0.0
        for i in range(len(coords) - 1):
            p1 = np.array(coords[i])
            p2 = np.array(coords[i + 1])
            actual_length += np.linalg.norm(p2 - p1)#linalg.norm calculates the Euclidean distance between two points
        
        # Calculate straight-line distance
        start = np.array(coords[0])
        end = np.array(coords[-1])
        straight_distance = np.linalg.norm(end - start)
        
        if straight_distance == 0:
            return 1.0
        
        sinuosity = actual_length / straight_distance
        return max(1.0, sinuosity)  # Minimum is 1.0
    
    def _calculate_bearing_changes(
        self,
        coords: List[Tuple[float, float]]
    ) -> List[float]:
        """
        Calculate bearing (compass direction) at each segment.
        Returns list of bearings in degrees (0-360).
        """
        bearings = []
        
        for i in range(len(coords) - 1):
            lon1, lat1 = coords[i]#destructure the coordinates into lat and lon
            lon2, lat2 = coords[i + 1]
            
            bearing = self._calculate_bearing(lat1, lon1, lat2, lon2)
            bearings.append(round(bearing, 2))
        
        return bearings
    
    def _calculate_bearing(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate initial bearing between two points.
        
        Returns bearing in degrees (0-360, where 0 is North).
        """
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        d_lon = math.radians(lon2 - lon1)
        
        # Calculate bearing
        x = math.sin(d_lon) * math.cos(lat2_rad)
        y = (math.cos(lat1_rad) * math.sin(lat2_rad) -
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(d_lon))
        
        bearing_rad = math.atan2(x, y)
        bearing_deg = math.degrees(bearing_rad)
        
        # Normalize to 0-360
        return (bearing_deg + 360) % 360
    
    def _calculate_avg_segment_length(
        self,
        coords: List[Tuple[float, float]]
    ) -> float:
        """Calculate average distance between consecutive coordinates."""
        if len(coords) < 2:
            return 0.0
        
        total_length = 0.0
        for i in range(len(coords) - 1):
            p1 = np.array(coords[i])
            p2 = np.array(coords[i + 1])
            total_length += np.linalg.norm(p2 - p1)
        
        return round(total_length / (len(coords) - 1), 2)
    
    def _angle_between_vectors(
        self,
        v1: np.ndarray,
        v2: np.ndarray
    ) -> float:
        """
        Calculate angle between two vectors in degrees.
        """
        # Normalize vectors
        v1_norm = v1 / (np.linalg.norm(v1) + 1e-10)
        v2_norm = v2 / (np.linalg.norm(v2) + 1e-10)
        
        # Calculate dot product
        dot_product = np.clip(np.dot(v1_norm, v2_norm), -1.0, 1.0)
        
        # Calculate angle in degrees
        angle = math.degrees(math.acos(dot_product))
        
        return angle
    
    def _empty_analysis(self) -> Dict[str, Any]:
        """Return empty analysis structure."""
        return {
            "curvature": 0.0,
            "turn_count": 0,
            "sinuosity": 1.0,
            "bearing_changes": [],
            "avg_segment_length": 0.0,
            "coordinate_count": 0
        }
    
    def estimate_width(
        self,
        segment: RoadSegment
    ) -> Optional[float]:
        """
        Estimate road width based on available data.
        
        Priority:
        1. Explicit width tag from OSM
        2. Lane count * standard lane width
        3. Road type heuristics
        """
        # Check for explicit width
        if segment.width and segment.width > 0:
            return segment.width
        
        # Estimate from lanes
        if segment.lanes:
            try:
                lanes = int(segment.lanes)
                # Standard lane width ~3.5m, add shoulder/parking
                return lanes * 3.5 + 2.0
            except (ValueError, TypeError):
                pass
        
        # Estimate from road type
        width_by_type = {
            "motorway": 14.0,      # 2 lanes each way + shoulder
            "trunk": 12.0,
            "primary": 10.0,
            "secondary": 8.0,
            "tertiary": 7.0,
            "residential": 6.0,
            "unclassified": 5.0,
            "service": 4.0,
            "track": 3.0
        }
        
        if segment.road_type:
            return width_by_type.get(segment.road_type.lower())
        
        return None
    
    def calculate_intersection_angle(
        self,
        segment1_coords: List[Tuple[float, float]],
        segment2_coords: List[Tuple[float, float]]
    ) -> Optional[float]:
        """
        Calculate intersection angle between two segments.
        
        Returns angle in degrees, or None if segments don't intersect.
        """
        try:
            line1 = LineString(segment1_coords)
            line2 = LineString(segment2_coords)
            
            if not line1.intersects(line2):
                return None
            
            # Get intersection point
            intersection = line1.intersection(line2)
            if not isinstance(intersection, Point):
                return None
            
            # Get bearings at intersection
            # Find closest point on each line to intersection
            dist1 = line1.project(intersection)
            dist2 = line2.project(intersection)
            
            # Get points just before and after intersection
            point1_before = substring(line1, max(0, dist1 - 10), dist1)
            point1_after = substring(line1, dist1, min(line1.length, dist1 + 10))
            
            point2_before = substring(line2, max(0, dist2 - 10), dist2)
            point2_after = substring(line2, dist2, min(line2.length, dist2 + 10))
            
            # Calculate bearings
            def get_bearing_at_point(line, distance):
                point = line.interpolate(distance)
                # Get nearby points for bearing
                p_before = substring(line, max(0, distance - 5), distance)
                p_after = substring(line, distance, min(line.length, distance + 5))
                if p_before and p_after:
                    return self._calculate_bearing(
                        p_before.y, p_before.x, p_after.y, p_after.x
                    )
                return None
            
            bearing1 = get_bearing_at_point(line1, dist1)
            bearing2 = get_bearing_at_point(line2, dist2)
            
            if bearing1 is None or bearing2 is None:
                return None
            
            # Calculate angle between bearings
            angle = abs(bearing1 - bearing2)
            if angle > 180:
                angle = 360 - angle
            
            return round(angle, 2)
            
        except Exception as e:
            print(f"Intersection calculation error: {e}")
            return None
