"""Route matrix calculation service using Yandex.Maps API."""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
import structlog
import aiohttp
from datetime import datetime, timedelta

from app.config import settings

logger = structlog.get_logger()


class RouteMatrixService:
    """
    Calculate route matrices for property listings to anchor points.

    Uses Yandex.Maps Routing API to calculate:
    - Transit time (public transport + walking)
    - Driving time
    - Walking time

    Requires: YANDEX_MAPS_API_KEY in settings.
    Free tier: 25,000 requests/month.
    """

    ROUTER_API_URL = "https://api.routing.yandex.net/v2/route"
    MATRIX_API_URL = "https://api.routing.yandex.net/v2/distancematrix"

    # Cache route data for 30 days (routes don't change frequently)
    CACHE_TTL_DAYS = 30

    # Transport modes
    MODE_TRANSIT = "transit"  # Public transport
    MODE_DRIVING = "driving"
    MODE_WALKING = "walking"

    def __init__(self):
        """Initialize route matrix service."""
        self.api_key = getattr(settings, 'yandex_maps_api_key', None)

        if not self.api_key:
            logger.warning("yandex_maps_not_configured",
                          message="Route matrix disabled. Set YANDEX_MAPS_API_KEY")

        self._cache: Dict[str, Dict[str, Any]] = {}
        logger.info("route_matrix_service_initialized",
                   api_configured=bool(self.api_key))

    async def calculate_routes(
        self,
        listing_id: str,
        from_latitude: float,
        from_longitude: float,
        anchor_points: List[Dict[str, Any]],
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate routes from listing to anchor points.

        Args:
            listing_id: Listing ID for caching
            from_latitude: Listing latitude
            from_longitude: Listing longitude
            anchor_points: List of dicts with {name, latitude, longitude, priority}
            force_refresh: Skip cache and fetch fresh data

        Returns:
            Route data dictionary:
            {
                "routes": {
                    "Work Office": {
                        "transit": {
                            "duration_minutes": int,
                            "distance_km": float,
                            "steps": List[str]  # Brief description
                        },
                        "driving": {...},
                        "walking": {...}
                    },
                    ...
                },
                "summary": {
                    "avg_transit_time": float,
                    "max_transit_time": int,
                    "closest_anchor": str,
                    "total_anchors": int
                },
                "calculated_at": str  # ISO timestamp
            }
        """
        if not self.api_key:
            logger.warning("route_calculation_skipped_no_api_key",
                          listing_id=listing_id)
            return self._empty_route_data()

        logger.info("calculating_routes",
                   listing_id=listing_id,
                   anchor_count=len(anchor_points))

        # Check cache
        cache_key = f"{listing_id}_{from_latitude}_{from_longitude}_{len(anchor_points)}"
        if not force_refresh and cache_key in self._cache:
            cached_data = self._cache[cache_key]
            calculated_at = datetime.fromisoformat(cached_data["calculated_at"])
            age = datetime.utcnow() - calculated_at

            if age < timedelta(days=self.CACHE_TTL_DAYS):
                logger.info("route_cache_hit",
                           listing_id=listing_id,
                           age_days=age.days)
                return cached_data

        # Calculate routes to each anchor
        try:
            routes = {}

            for anchor in anchor_points:
                anchor_name = anchor.get("name", "Unknown")
                anchor_lat = anchor.get("latitude")
                anchor_lon = anchor.get("longitude")

                if not anchor_lat or not anchor_lon:
                    logger.warning("anchor_missing_coordinates",
                                  anchor_name=anchor_name)
                    continue

                # Calculate all transport modes
                anchor_routes = await self._calculate_anchor_routes(
                    from_lat=from_latitude,
                    from_lon=from_longitude,
                    to_lat=anchor_lat,
                    to_lon=anchor_lon
                )

                routes[anchor_name] = anchor_routes

                # Small delay for rate limiting
                await asyncio.sleep(0.1)

            # Build summary
            summary = self._build_route_summary(routes)

            route_data = {
                "routes": routes,
                "summary": summary,
                "calculated_at": datetime.utcnow().isoformat()
            }

            # Cache result
            self._cache[cache_key] = route_data

            logger.info("route_calculation_success",
                       listing_id=listing_id,
                       anchors_calculated=len(routes))

            return route_data

        except Exception as e:
            logger.error("route_calculation_error",
                        listing_id=listing_id,
                        error=str(e))
            return self._empty_route_data()

    async def _calculate_anchor_routes(
        self,
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float
    ) -> Dict[str, Any]:
        """
        Calculate routes for all transport modes to single anchor.

        Args:
            from_lat, from_lon: Origin coordinates
            to_lat, to_lon: Destination coordinates

        Returns:
            Routes for transit, driving, walking
        """
        # Calculate all modes concurrently
        tasks = [
            self._calculate_single_route(
                from_lat, from_lon, to_lat, to_lon, self.MODE_TRANSIT
            ),
            self._calculate_single_route(
                from_lat, from_lon, to_lat, to_lon, self.MODE_DRIVING
            ),
            self._calculate_single_route(
                from_lat, from_lon, to_lat, to_lon, self.MODE_WALKING
            )
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        transit_route, driving_route, walking_route = results

        return {
            "transit": transit_route if not isinstance(transit_route, Exception) else None,
            "driving": driving_route if not isinstance(driving_route, Exception) else None,
            "walking": walking_route if not isinstance(walking_route, Exception) else None
        }

    async def _calculate_single_route(
        self,
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float,
        mode: str
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate single route with specific transport mode.

        Args:
            from_lat, from_lon: Origin coordinates
            to_lat, to_lon: Destination coordinates
            mode: Transport mode (transit/driving/walking)

        Returns:
            Route data or None if failed
        """
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "apikey": self.api_key,
                    "origin": f"{from_lon},{from_lat}",  # Yandex uses lon,lat
                    "destination": f"{to_lon},{to_lat}",
                    "mode": mode
                }

                async with session.get(
                    self.ROUTER_API_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error("yandex_router_api_error",
                                   status=response.status,
                                   error=error_text,
                                   mode=mode)
                        return None

                    data = await response.json()

            # Parse response
            route_info = self._parse_yandex_route(data, mode)
            return route_info

        except Exception as e:
            logger.error("route_calculation_error",
                        mode=mode,
                        error=str(e))
            return None

    def _parse_yandex_route(
        self,
        data: Dict[str, Any],
        mode: str
    ) -> Dict[str, Any]:
        """
        Parse Yandex Router API response.

        Args:
            data: Raw API response
            mode: Transport mode

        Returns:
            Parsed route info
        """
        try:
            # Yandex Router API response structure:
            # {
            #   "route": {
            #     "distance": {"value": meters, "text": "5.2 km"},
            #     "duration": {"value": seconds, "text": "25 min"},
            #     "legs": [...]
            #   }
            # }

            route = data.get("route", {})

            distance_data = route.get("distance", {})
            duration_data = route.get("duration", {})

            distance_meters = distance_data.get("value", 0)
            duration_seconds = duration_data.get("value", 0)

            # Extract brief steps (for transit mode)
            steps = []
            if mode == self.MODE_TRANSIT:
                legs = route.get("legs", [])
                for leg in legs:
                    for step in leg.get("steps", []):
                        transit_info = step.get("transit_details", {})
                        if transit_info:
                            line = transit_info.get("line", {})
                            line_name = line.get("name", "")
                            if line_name:
                                steps.append(line_name)

            return {
                "duration_minutes": round(duration_seconds / 60),
                "distance_km": round(distance_meters / 1000, 1),
                "steps": steps[:5] if steps else []  # Max 5 steps
            }

        except Exception as e:
            logger.error("route_parse_error", error=str(e))
            return {
                "duration_minutes": None,
                "distance_km": None,
                "steps": []
            }

    def _build_route_summary(
        self,
        routes: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build summary statistics from all routes.

        Args:
            routes: Dictionary of routes by anchor name

        Returns:
            Summary statistics
        """
        transit_times = []
        closest_anchor = None
        min_time = float('inf')

        for anchor_name, anchor_routes in routes.items():
            transit = anchor_routes.get("transit")
            if transit and transit.get("duration_minutes"):
                duration = transit["duration_minutes"]
                transit_times.append(duration)

                if duration < min_time:
                    min_time = duration
                    closest_anchor = anchor_name

        if not transit_times:
            return {
                "avg_transit_time": None,
                "max_transit_time": None,
                "closest_anchor": None,
                "total_anchors": len(routes)
            }

        return {
            "avg_transit_time": round(sum(transit_times) / len(transit_times), 1),
            "max_transit_time": max(transit_times),
            "closest_anchor": closest_anchor,
            "total_anchors": len(routes)
        }

    def _empty_route_data(self) -> Dict[str, Any]:
        """Return empty route data structure."""
        return {
            "routes": {},
            "summary": {
                "avg_transit_time": None,
                "max_transit_time": None,
                "closest_anchor": None,
                "total_anchors": 0
            },
            "calculated_at": datetime.utcnow().isoformat()
        }

    def get_route_summary(
        self,
        route_data: Dict[str, Any],
        max_anchors: int = 3
    ) -> str:
        """
        Generate human-readable route summary.

        Args:
            route_data: Route data from calculate_routes()
            max_anchors: Max anchors to show

        Returns:
            Human-readable summary in Russian
        """
        routes = route_data.get("routes", {})
        summary = route_data.get("summary", {})

        if not routes:
            return "Маршруты: данные недоступны"

        parts = []

        # Show top anchors by transit time
        sorted_routes = sorted(
            routes.items(),
            key=lambda x: x[1].get("transit", {}).get("duration_minutes") or 999
        )

        for anchor_name, anchor_routes in sorted_routes[:max_anchors]:
            transit = anchor_routes.get("transit")
            if transit and transit.get("duration_minutes"):
                duration = transit["duration_minutes"]
                distance = transit["distance_km"]
                parts.append(f"🚇 {anchor_name}: {duration} мин ({distance} км)")

        # Add average if multiple anchors
        avg_time = summary.get("avg_transit_time")
        if avg_time and len(routes) > 1:
            parts.append(f"\nСреднее время: {int(avg_time)} мин")

        return "\n".join(parts) if parts else "Маршруты: не рассчитаны"


# Global instance
route_matrix_service = RouteMatrixService()
