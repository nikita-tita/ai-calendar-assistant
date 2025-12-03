"""POI (Points of Interest) enrichment service using OpenStreetMap."""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
import structlog
import aiohttp
from datetime import datetime, timedelta

logger = structlog.get_logger()


class POIEnrichmentService:
    """
    Enrich property listings with nearby Points of Interest data.

    Uses Overpass API (OpenStreetMap) to find:
    - Schools (amenity=school)
    - Kindergartens (amenity=kindergarten)
    - Parks (leisure=park)
    - Supermarkets (shop=supermarket)
    - Pharmacies (amenity=pharmacy)
    - Public transport (public_transport=stop_position)

    Free, no API key required, rate limit: ~2 requests/second.
    """

    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    WALKING_DISTANCE_METERS = 800  # ~10 min walk
    NEARBY_THRESHOLD_METERS = 500  # "Very close"

    # Cache POI data for 7 days (POI don't change frequently)
    CACHE_TTL_DAYS = 7

    def __init__(self):
        """Initialize POI enrichment service."""
        self._cache: Dict[str, Dict[str, Any]] = {}
        logger.info("poi_enrichment_service_initialized")

    async def enrich_listing(
        self,
        listing_id: str,
        latitude: float,
        longitude: float,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Enrich single listing with POI data.

        Args:
            listing_id: Listing ID for caching
            latitude: Listing latitude
            longitude: Listing longitude
            force_refresh: Skip cache and fetch fresh data

        Returns:
            POI data dictionary:
            {
                "school": {
                    "nearby": bool,  # Within 800m
                    "count": int,  # Number found
                    "closest_distance": float,  # Meters
                    "closest_name": str,
                    "all": List[Dict]  # All schools found
                },
                "kindergarten": {...},
                "park": {...},
                "supermarket": {...},
                "pharmacy": {...},
                "public_transport": {...},
                "enriched_at": str  # ISO timestamp
            }
        """
        logger.info("enriching_listing_with_poi",
                   listing_id=listing_id,
                   lat=latitude,
                   lon=longitude)

        # Check cache
        cache_key = f"{listing_id}_{latitude}_{longitude}"
        if not force_refresh and cache_key in self._cache:
            cached_data = self._cache[cache_key]
            enriched_at = datetime.fromisoformat(cached_data["enriched_at"])
            age = datetime.utcnow() - enriched_at

            if age < timedelta(days=self.CACHE_TTL_DAYS):
                logger.info("poi_cache_hit", listing_id=listing_id, age_days=age.days)
                return cached_data

        # Fetch POI data from OpenStreetMap
        try:
            poi_data = await self._fetch_poi_from_osm(latitude, longitude)
            poi_data["enriched_at"] = datetime.utcnow().isoformat()

            # Cache result
            self._cache[cache_key] = poi_data

            logger.info("poi_enrichment_success",
                       listing_id=listing_id,
                       schools=poi_data["school"]["count"],
                       kindergartens=poi_data["kindergarten"]["count"],
                       parks=poi_data["park"]["count"])

            return poi_data

        except Exception as e:
            logger.error("poi_enrichment_error",
                        listing_id=listing_id,
                        error=str(e))

            # Return empty POI data on error
            return self._empty_poi_data()

    async def enrich_listings_batch(
        self,
        listings: List[Dict[str, Any]],
        batch_size: int = 10,
        delay_seconds: float = 0.5
    ) -> Dict[str, Dict[str, Any]]:
        """
        Enrich multiple listings with POI data in batches.

        Args:
            listings: List of dicts with {id, latitude, longitude}
            batch_size: Number of concurrent requests
            delay_seconds: Delay between batches (rate limiting)

        Returns:
            Dictionary {listing_id: poi_data}
        """
        logger.info("batch_enrichment_start",
                   total_listings=len(listings),
                   batch_size=batch_size)

        results = {}
        total_batches = (len(listings) + batch_size - 1) // batch_size

        for batch_idx in range(0, len(listings), batch_size):
            batch = listings[batch_idx:batch_idx + batch_size]

            # Process batch concurrently
            tasks = [
                self.enrich_listing(
                    listing_id=listing["id"],
                    latitude=listing["latitude"],
                    longitude=listing["longitude"]
                )
                for listing in batch
                if listing.get("latitude") and listing.get("longitude")
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Store results
            for listing, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error("batch_item_error",
                               listing_id=listing["id"],
                               error=str(result))
                    results[listing["id"]] = self._empty_poi_data()
                else:
                    results[listing["id"]] = result

            current_batch = batch_idx // batch_size + 1
            logger.info("batch_completed",
                       batch=f"{current_batch}/{total_batches}",
                       processed=len(results))

            # Rate limiting delay between batches
            if current_batch < total_batches:
                await asyncio.sleep(delay_seconds)

        logger.info("batch_enrichment_complete",
                   total_enriched=len(results))

        return results

    async def _fetch_poi_from_osm(
        self,
        latitude: float,
        longitude: float
    ) -> Dict[str, Any]:
        """
        Fetch POI data from OpenStreetMap Overpass API.

        Args:
            latitude: Center point latitude
            longitude: Center point longitude

        Returns:
            Structured POI data
        """
        # Build Overpass QL query
        radius = self.WALKING_DISTANCE_METERS
        query = self._build_overpass_query(latitude, longitude, radius)

        # Call Overpass API
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.OVERPASS_URL,
                data={"data": query},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Overpass API error: {response.status} - {error_text}")

                data = await response.json()

        # Parse response
        poi_data = self._parse_overpass_response(data, latitude, longitude)

        return poi_data

    def _build_overpass_query(
        self,
        latitude: float,
        longitude: float,
        radius: int
    ) -> str:
        """
        Build Overpass QL query for POI search.

        Query structure:
        - Search around point (lat, lon) with radius
        - Find all amenity=school, kindergarten, pharmacy
        - Find all leisure=park
        - Find all shop=supermarket
        - Find all public_transport stops
        - Output as JSON with tags
        """
        query = f"""
[out:json][timeout:25];
(
  // Schools
  node["amenity"="school"](around:{radius},{latitude},{longitude});
  way["amenity"="school"](around:{radius},{latitude},{longitude});

  // Kindergartens
  node["amenity"="kindergarten"](around:{radius},{latitude},{longitude});
  way["amenity"="kindergarten"](around:{radius},{latitude},{longitude});

  // Parks
  node["leisure"="park"](around:{radius},{latitude},{longitude});
  way["leisure"="park"](around:{radius},{latitude},{longitude});

  // Supermarkets
  node["shop"="supermarket"](around:{radius},{latitude},{longitude});
  way["shop"="supermarket"](around:{radius},{latitude},{longitude});

  // Pharmacies
  node["amenity"="pharmacy"](around:{radius},{latitude},{longitude});
  way["amenity"="pharmacy"](around:{radius},{latitude},{longitude});

  // Public transport stops
  node["public_transport"="stop_position"](around:{radius},{latitude},{longitude});
  node["highway"="bus_stop"](around:{radius},{latitude},{longitude});
);
out center;
"""
        return query.strip()

    def _parse_overpass_response(
        self,
        data: Dict[str, Any],
        center_lat: float,
        center_lon: float
    ) -> Dict[str, Any]:
        """
        Parse Overpass API response into structured POI data.

        Args:
            data: Raw Overpass API response
            center_lat: Center point latitude
            center_lon: Center point longitude

        Returns:
            Structured POI data by category
        """
        elements = data.get("elements", [])

        # Categorize POI by type
        schools = []
        kindergartens = []
        parks = []
        supermarkets = []
        pharmacies = []
        public_transport = []

        for element in elements:
            tags = element.get("tags", {})
            amenity = tags.get("amenity")
            leisure = tags.get("leisure")
            shop = tags.get("shop")
            public_transport_type = tags.get("public_transport")
            highway = tags.get("highway")

            # Get coordinates (from node or way center)
            if element["type"] == "node":
                lat = element.get("lat")
                lon = element.get("lon")
            else:  # way
                center = element.get("center", {})
                lat = center.get("lat")
                lon = center.get("lon")

            if not lat or not lon:
                continue

            # Calculate distance
            distance = self._haversine_distance(
                center_lat, center_lon,
                lat, lon
            )

            poi_item = {
                "name": tags.get("name", "Без названия"),
                "latitude": lat,
                "longitude": lon,
                "distance_meters": round(distance, 1),
                "tags": tags
            }

            # Categorize
            if amenity == "school":
                schools.append(poi_item)
            elif amenity == "kindergarten":
                kindergartens.append(poi_item)
            elif leisure == "park":
                parks.append(poi_item)
            elif shop == "supermarket":
                supermarkets.append(poi_item)
            elif amenity == "pharmacy":
                pharmacies.append(poi_item)
            elif public_transport_type == "stop_position" or highway == "bus_stop":
                public_transport.append(poi_item)

        # Build structured result
        result = {
            "school": self._build_poi_category_data(schools),
            "kindergarten": self._build_poi_category_data(kindergartens),
            "park": self._build_poi_category_data(parks),
            "supermarket": self._build_poi_category_data(supermarkets),
            "pharmacy": self._build_poi_category_data(pharmacies),
            "public_transport": self._build_poi_category_data(public_transport)
        }

        return result

    def _build_poi_category_data(self, pois: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build category summary data.

        Args:
            pois: List of POI items in category

        Returns:
            Category summary with nearby flag, count, closest, etc.
        """
        if not pois:
            return {
                "nearby": False,
                "count": 0,
                "closest_distance": None,
                "closest_name": None,
                "all": []
            }

        # Sort by distance
        pois_sorted = sorted(pois, key=lambda x: x["distance_meters"])

        closest = pois_sorted[0]

        return {
            "nearby": closest["distance_meters"] <= self.WALKING_DISTANCE_METERS,
            "count": len(pois),
            "closest_distance": closest["distance_meters"],
            "closest_name": closest["name"],
            "all": pois_sorted[:5]  # Top 5 closest
        }

    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate distance between two points using Haversine formula.

        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates

        Returns:
            Distance in meters
        """
        from math import radians, sin, cos, sqrt, atan2

        # Earth radius in meters
        R = 6371000

        # Convert to radians
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)

        # Haversine formula
        a = sin(delta_lat / 2) ** 2 + \
            cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = R * c

        return distance

    def _empty_poi_data(self) -> Dict[str, Any]:
        """Return empty POI data structure."""
        empty_category = {
            "nearby": False,
            "count": 0,
            "closest_distance": None,
            "closest_name": None,
            "all": []
        }

        return {
            "school": empty_category.copy(),
            "kindergarten": empty_category.copy(),
            "park": empty_category.copy(),
            "supermarket": empty_category.copy(),
            "pharmacy": empty_category.copy(),
            "public_transport": empty_category.copy(),
            "enriched_at": datetime.utcnow().isoformat()
        }

    def get_poi_summary(self, poi_data: Dict[str, Any]) -> str:
        """
        Generate human-readable POI summary.

        Args:
            poi_data: POI data from enrich_listing()

        Returns:
            Human-readable summary in Russian
        """
        parts = []

        # Schools
        school = poi_data.get("school", {})
        if school.get("nearby"):
            distance = school["closest_distance"]
            name = school["closest_name"]
            parts.append(f"🏫 Школа ({int(distance)}м): {name}")

        # Kindergartens
        kindergarten = poi_data.get("kindergarten", {})
        if kindergarten.get("nearby"):
            distance = kindergarten["closest_distance"]
            name = kindergarten["closest_name"]
            parts.append(f"👶 Детский сад ({int(distance)}м): {name}")

        # Parks
        park = poi_data.get("park", {})
        if park.get("nearby"):
            distance = park["closest_distance"]
            name = park["closest_name"]
            parts.append(f"🌳 Парк ({int(distance)}м): {name}")

        # Supermarkets
        supermarket = poi_data.get("supermarket", {})
        if supermarket.get("count") > 0:
            distance = supermarket["closest_distance"]
            count = supermarket["count"]
            parts.append(f"🛒 Магазины: {count} ({int(distance)}м до ближайшего)")

        # Public transport
        transport = poi_data.get("public_transport", {})
        if transport.get("count") > 0:
            distance = transport["closest_distance"]
            parts.append(f"🚌 Остановка ({int(distance)}м)")

        if not parts:
            return "Инфраструктура: данные не найдены"

        return "\n".join(parts)


# Global instance
poi_enrichment_service = POIEnrichmentService()
