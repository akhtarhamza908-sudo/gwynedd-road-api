"""
Elevation service using the Open-Elevation API.
"""
from typing import List, Tuple, Dict, Any, Optional

import httpx

from app.core.config import get_settings

settings = get_settings()


class ElevationService:
    """
    Service for fetching elevation data and computing elevation profiles.
    Falls back gracefully when the external service is unavailable.
    """

    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url or settings.ELEVATION_API_URL
        self._client: Optional[httpx.AsyncClient] = httpx.AsyncClient(timeout=30.0)

    async def analyze_segment_elevation(
        self,
        coords: List[Tuple[float, float]],
        segment_length_m: float
    ) -> Dict[str, Any]:
        if not coords or len(coords) < 2 or segment_length_m <= 0:
            return self._empty_profile()

        elevations = await self._fetch_elevations(coords)
        if not elevations or len(elevations) < 2:
            return self._empty_profile()

        gain = 0.0
        loss = 0.0
        max_slope = 0.0
        total_slope = 0.0
        slope_count = 0

        for i in range(len(elevations) - 1):
            delta = elevations[i + 1] - elevations[i]
            if delta > 0:
                gain += delta
            else:
                loss += abs(delta)

            step_distance = segment_length_m / (len(elevations) - 1)
            if step_distance > 0:
                slope_percent = abs(delta) / step_distance * 100
                max_slope = max(max_slope, slope_percent)
                total_slope += slope_percent
                slope_count += 1

        avg_slope = total_slope / slope_count if slope_count > 0 else 0.0

        return {
            "elevation_gain": round(gain, 2),
            "elevation_loss": round(loss, 2),
            "max_slope": round(max_slope, 2),
            "avg_slope": round(avg_slope, 2),
            "start_elevation": round(elevations[0], 2),
            "end_elevation": round(elevations[-1], 2),
            "sample_count": len(elevations)
        }

    async def _fetch_elevations(self, coords: List[Tuple[float, float]]) -> List[float]:
        if self._client is None:
            return []

        payload = {
            "locations": [
                {"latitude": lat, "longitude": lon}
                for lat, lon in coords
            ]
        }

        try:
            response = await self._client.post(self.api_url, json=payload)
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            return [r.get("elevation", 0.0) for r in results]
        except Exception as e:
            print(f"Elevation API error: {e}")
            return []

    def _empty_profile(self) -> Dict[str, Any]:
        return {
            "elevation_gain": 0.0,
            "elevation_loss": 0.0,
            "max_slope": 0.0,
            "avg_slope": 0.0,
            "start_elevation": None,
            "end_elevation": None,
            "sample_count": 0
        }

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
