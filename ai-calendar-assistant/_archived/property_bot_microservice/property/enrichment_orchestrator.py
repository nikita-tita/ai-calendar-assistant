"""Enrichment orchestrator - coordinates all enrichment services."""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from app.schemas.property import PropertyListingResponse, PropertyClientResponse
from app.services.property.poi_enrichment import poi_enrichment_service
from app.services.property.route_matrix import route_matrix_service
from app.services.property.vision_analysis import vision_analysis_service
from app.services.property.price_context import price_context_service
from app.services.property.developer_reputation import developer_reputation_service

logger = structlog.get_logger()


class EnrichmentOrchestrator:
    """
    Orchestrate all enrichment services for property listings.

    Coordinates:
    1. POI enrichment (OpenStreetMap)
    2. Route calculations (Yandex.Maps)
    3. Vision analysis (Yandex Vision)
    4. Price context (market comparison)
    5. Developer reputation

    Handles parallel execution, error recovery, and progress tracking.
    """

    def __init__(self):
        """Initialize enrichment orchestrator."""
        self.poi_service = poi_enrichment_service
        self.route_service = route_matrix_service
        self.vision_service = vision_analysis_service
        self.price_service = price_context_service
        self.dev_service = developer_reputation_service

        logger.info("enrichment_orchestrator_initialized")

    async def enrich_listing_full(
        self,
        listing: PropertyListingResponse,
        client: Optional[PropertyClientResponse] = None,
        all_listings: Optional[List[Dict[str, Any]]] = None,
        enable_poi: bool = True,
        enable_routes: bool = True,
        enable_vision: bool = True,
        enable_price: bool = True,
        enable_developer: bool = True
    ) -> Dict[str, Any]:
        """
        Enrich single listing with all available data.

        Args:
            listing: Property listing to enrich
            client: Client profile (for route calculations)
            all_listings: All listings for price context
            enable_*: Feature flags for each enrichment type

        Returns:
            Complete enrichment data:
            {
                "listing_id": str,
                "poi_data": Dict,
                "route_data": Dict,
                "vision_data": Dict,
                "price_context": Dict,
                "developer_reputation": Dict,
                "enrichment_summary": str,  # Human-readable
                "enrichment_score": float,  # 0-100, completeness
                "enriched_at": str,
                "errors": List[str]  # Any errors encountered
            }
        """
        logger.info("enriching_listing_full",
                   listing_id=listing.id,
                   listing_title=listing.title)

        start_time = datetime.utcnow()
        errors = []

        # Prepare tasks for parallel execution
        tasks = []
        task_names = []

        # POI enrichment
        if enable_poi and listing.latitude and listing.longitude:
            tasks.append(self._enrich_poi_safe(listing))
            task_names.append("poi")
        else:
            tasks.append(self._empty_result("poi"))
            task_names.append("poi")

        # Route calculations
        if enable_routes and listing.latitude and listing.longitude and \
           client and client.anchor_points:
            tasks.append(self._enrich_routes_safe(listing, client))
            task_names.append("routes")
        else:
            tasks.append(self._empty_result("routes"))
            task_names.append("routes")

        # Vision analysis
        if enable_vision and listing.images:
            tasks.append(self._enrich_vision_safe(listing))
            task_names.append("vision")
        else:
            tasks.append(self._empty_result("vision"))
            task_names.append("vision")

        # Price context
        if enable_price and all_listings:
            tasks.append(self._enrich_price_safe(listing, all_listings))
            task_names.append("price")
        else:
            tasks.append(self._empty_result("price"))
            task_names.append("price")

        # Developer reputation
        if enable_developer and listing.developer_name:
            tasks.append(self._enrich_developer_safe(listing))
            task_names.append("developer")
        else:
            tasks.append(self._empty_result("developer"))
            task_names.append("developer")

        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        enrichment_data = {
            "listing_id": listing.id,
            "poi_data": None,
            "route_data": None,
            "vision_data": None,
            "price_context": None,
            "developer_reputation": None,
            "enriched_at": datetime.utcnow().isoformat(),
            "errors": []
        }

        for task_name, result in zip(task_names, results):
            if isinstance(result, Exception):
                error_msg = f"{task_name}_error: {str(result)}"
                errors.append(error_msg)
                logger.error("enrichment_task_failed",
                           task=task_name,
                           error=str(result))
            else:
                enrichment_data[f"{task_name}_data" if task_name != "developer" else "developer_reputation"] = result

        enrichment_data["errors"] = errors

        # Calculate enrichment completeness score
        enrichment_score = self._calculate_enrichment_score(enrichment_data)
        enrichment_data["enrichment_score"] = enrichment_score

        # Generate human-readable summary
        summary = self._generate_enrichment_summary(enrichment_data)
        enrichment_data["enrichment_summary"] = summary

        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info("enrichment_completed",
                   listing_id=listing.id,
                   score=enrichment_score,
                   elapsed_seconds=round(elapsed, 2),
                   errors_count=len(errors))

        return enrichment_data

    async def enrich_listings_batch(
        self,
        listings: List[PropertyListingResponse],
        client: Optional[PropertyClientResponse] = None,
        all_listings: Optional[List[Dict[str, Any]]] = None,
        batch_size: int = 5,
        **enrichment_flags
    ) -> Dict[str, Dict[str, Any]]:
        """
        Enrich multiple listings in batches.

        Args:
            listings: List of listings to enrich
            client: Client profile
            all_listings: All listings for price context
            batch_size: Number of concurrent enrichments
            **enrichment_flags: Feature flags (enable_poi, etc.)

        Returns:
            Dictionary {listing_id: enrichment_data}
        """
        logger.info("batch_enrichment_start",
                   total_listings=len(listings),
                   batch_size=batch_size)

        results = {}
        total_batches = (len(listings) + batch_size - 1) // batch_size

        for batch_idx in range(0, len(listings), batch_size):
            batch = listings[batch_idx:batch_idx + batch_size]

            # Enrich batch in parallel
            tasks = [
                self.enrich_listing_full(
                    listing=listing,
                    client=client,
                    all_listings=all_listings,
                    **enrichment_flags
                )
                for listing in batch
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Store results
            for listing, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error("batch_enrichment_item_error",
                               listing_id=listing.id,
                               error=str(result))
                    results[listing.id] = {
                        "listing_id": listing.id,
                        "errors": [f"enrichment_failed: {str(result)}"],
                        "enrichment_score": 0
                    }
                else:
                    results[listing.id] = result

            current_batch = batch_idx // batch_size + 1
            logger.info("batch_enrichment_progress",
                       batch=f"{current_batch}/{total_batches}",
                       processed=len(results))

            # Small delay between batches
            if current_batch < total_batches:
                await asyncio.sleep(0.3)

        logger.info("batch_enrichment_complete",
                   total_enriched=len(results))

        return results

    async def _enrich_poi_safe(self, listing: PropertyListingResponse) -> Dict[str, Any]:
        """Safely enrich POI data with error handling."""
        try:
            return await self.poi_service.enrich_listing(
                listing_id=listing.id,
                latitude=listing.latitude,
                longitude=listing.longitude
            )
        except Exception as e:
            logger.error("poi_enrichment_failed", listing_id=listing.id, error=str(e))
            return self.poi_service._empty_poi_data()

    async def _enrich_routes_safe(
        self,
        listing: PropertyListingResponse,
        client: PropertyClientResponse
    ) -> Dict[str, Any]:
        """Safely enrich route data with error handling."""
        try:
            return await self.route_service.calculate_routes(
                listing_id=listing.id,
                from_latitude=listing.latitude,
                from_longitude=listing.longitude,
                anchor_points=client.anchor_points or []
            )
        except Exception as e:
            logger.error("route_enrichment_failed", listing_id=listing.id, error=str(e))
            return self.route_service._empty_route_data()

    async def _enrich_vision_safe(self, listing: PropertyListingResponse) -> Dict[str, Any]:
        """Safely enrich vision data with error handling."""
        try:
            return await self.vision_service.analyze_listing_images(
                listing_id=listing.id,
                image_urls=listing.images or []
            )
        except Exception as e:
            logger.error("vision_enrichment_failed", listing_id=listing.id, error=str(e))
            return self.vision_service._empty_vision_data()

    async def _enrich_price_safe(
        self,
        listing: PropertyListingResponse,
        all_listings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Safely enrich price context with error handling."""
        try:
            return await self.price_service.analyze_listing_price(
                listing_id=listing.id,
                price=listing.price,
                area_total=listing.area_total,
                rooms=listing.rooms,
                district=listing.district,
                building_type=listing.building_type,
                renovation=listing.renovation,
                all_listings=all_listings
            )
        except Exception as e:
            logger.error("price_enrichment_failed", listing_id=listing.id, error=str(e))
            return self.price_service._empty_price_context()

    async def _enrich_developer_safe(self, listing: PropertyListingResponse) -> Dict[str, Any]:
        """Safely enrich developer reputation with error handling."""
        try:
            return await self.dev_service.get_developer_reputation(
                developer_name=listing.developer_name
            )
        except Exception as e:
            logger.error("developer_enrichment_failed", listing_id=listing.id, error=str(e))
            return self.dev_service._unknown_developer_data(listing.developer_name)

    async def _empty_result(self, enrichment_type: str) -> Dict[str, Any]:
        """Return empty result for disabled enrichment."""
        return {"enrichment_type": enrichment_type, "enabled": False}

    def _calculate_enrichment_score(self, enrichment_data: Dict[str, Any]) -> float:
        """
        Calculate enrichment completeness score (0-100).

        Weights:
        - POI: 20%
        - Routes: 20%
        - Vision: 25%
        - Price: 20%
        - Developer: 15%
        """
        score = 0.0

        # POI (20 points)
        poi_data = enrichment_data.get("poi_data")
        if poi_data and poi_data.get("enrichment_type") != "poi":
            # Check if any POI found
            has_school = poi_data.get("school", {}).get("count", 0) > 0
            has_kindergarten = poi_data.get("kindergarten", {}).get("count", 0) > 0
            has_park = poi_data.get("park", {}).get("count", 0) > 0

            if has_school or has_kindergarten or has_park:
                score += 20.0
            else:
                score += 10.0  # Partial - data retrieved but nothing found

        # Routes (20 points)
        route_data = enrichment_data.get("route_data")
        if route_data and route_data.get("enrichment_type") != "routes":
            routes_count = len(route_data.get("routes", {}))
            if routes_count > 0:
                score += 20.0
            else:
                score += 5.0

        # Vision (25 points)
        vision_data = enrichment_data.get("vision_data")
        if vision_data and vision_data.get("enrichment_type") != "vision":
            images_analyzed = vision_data.get("images_analyzed", 0)
            if images_analyzed > 0:
                score += 25.0
            else:
                score += 5.0

        # Price (20 points)
        price_data = enrichment_data.get("price_context")
        if price_data and price_data.get("enrichment_type") != "price":
            if price_data.get("comparable_count", 0) > 0:
                score += 20.0
            else:
                score += 5.0

        # Developer (15 points)
        dev_data = enrichment_data.get("developer_reputation")
        if dev_data and dev_data.get("enrichment_type") != "developer":
            if dev_data.get("tier") != "unknown":
                score += 15.0
            else:
                score += 3.0

        return round(score, 1)

    def _generate_enrichment_summary(self, enrichment_data: Dict[str, Any]) -> str:
        """Generate human-readable enrichment summary."""
        parts = []

        # POI
        poi_data = enrichment_data.get("poi_data")
        if poi_data and poi_data.get("school", {}).get("nearby"):
            school_dist = poi_data["school"]["closest_distance"]
            parts.append(f"🏫 Школа ({int(school_dist)}м)")

        if poi_data and poi_data.get("kindergarten", {}).get("nearby"):
            kg_dist = poi_data["kindergarten"]["closest_distance"]
            parts.append(f"👶 Детский сад ({int(kg_dist)}м)")

        # Routes
        route_data = enrichment_data.get("route_data")
        if route_data and route_data.get("summary", {}).get("avg_transit_time"):
            avg_time = route_data["summary"]["avg_transit_time"]
            parts.append(f"🚇 Среднее время в пути: {int(avg_time)} мин")

        # Vision
        vision_data = enrichment_data.get("vision_data")
        if vision_data and vision_data.get("light_score"):
            light_score = vision_data["light_score"]
            if light_score >= 0.7:
                parts.append("💡 Очень светлая квартира")

        # Price
        price_data = enrichment_data.get("price_context")
        if price_data and price_data.get("value_assessment"):
            value = price_data["value_assessment"]
            value_emoji = {
                "deal": "💰",
                "good_value": "✅",
                "fair": "⚖️",
                "above_average": "📊",
                "expensive": "💸"
            }
            emoji = value_emoji.get(value, "")
            parts.append(f"{emoji} {value.replace('_', ' ').title()}")

        # Developer
        dev_data = enrichment_data.get("developer_reputation")
        if dev_data and dev_data.get("tier"):
            tier = dev_data["tier"]
            tier_emoji = {
                "premium": "⭐",
                "reliable": "✅",
                "average": "⚖️",
                "caution": "⚠️",
                "unknown": "❓"
            }
            emoji = tier_emoji.get(tier, "")
            parts.append(f"{emoji} Застройщик: {tier}")

        # Enrichment score
        score = enrichment_data.get("enrichment_score", 0)
        parts.append(f"📊 Полнота данных: {score}/100")

        if not parts:
            return "Данные обогащения недоступны"

        return "\n".join(parts)

    def get_enrichment_report(
        self,
        enrichment_data: Dict[str, Any],
        detailed: bool = False
    ) -> str:
        """
        Generate detailed enrichment report.

        Args:
            enrichment_data: Enrichment data from enrich_listing_full()
            detailed: Include full details or just summary

        Returns:
            Formatted report
        """
        if not detailed:
            return enrichment_data.get("enrichment_summary", "")

        # Detailed report
        report_parts = []

        report_parts.append("=" * 50)
        report_parts.append(f"ENRICHMENT REPORT - {enrichment_data['listing_id']}")
        report_parts.append("=" * 50)

        # Score
        score = enrichment_data.get("enrichment_score", 0)
        report_parts.append(f"\n📊 Enrichment Score: {score}/100")

        # POI
        poi_data = enrichment_data.get("poi_data")
        if poi_data and poi_data.get("enrichment_type") != "poi":
            report_parts.append("\n🏘️ INFRASTRUCTURE (POI):")
            summary = self.poi_service.get_poi_summary(poi_data)
            report_parts.append(summary)

        # Routes
        route_data = enrichment_data.get("route_data")
        if route_data and route_data.get("enrichment_type") != "routes":
            report_parts.append("\n🚇 COMMUTE TIMES:")
            summary = self.route_service.get_route_summary(route_data)
            report_parts.append(summary)

        # Vision
        vision_data = enrichment_data.get("vision_data")
        if vision_data and vision_data.get("enrichment_type") != "vision":
            report_parts.append("\n📸 PHOTO ANALYSIS:")
            summary = self.vision_service.get_vision_summary(vision_data)
            report_parts.append(summary)

        # Price
        price_data = enrichment_data.get("price_context")
        if price_data and price_data.get("enrichment_type") != "price":
            report_parts.append("\n💰 MARKET CONTEXT:")
            summary = self.price_service.get_price_summary(price_data)
            report_parts.append(summary)

        # Developer
        dev_data = enrichment_data.get("developer_reputation")
        if dev_data and dev_data.get("enrichment_type") != "developer":
            report_parts.append("\n🏗️ DEVELOPER:")
            summary = self.dev_service.get_reputation_summary(dev_data)
            report_parts.append(summary)

        # Errors
        errors = enrichment_data.get("errors", [])
        if errors:
            report_parts.append("\n⚠️ ERRORS:")
            for error in errors:
                report_parts.append(f"  - {error}")

        report_parts.append("\n" + "=" * 50)

        return "\n".join(report_parts)


# Global instance
enrichment_orchestrator = EnrichmentOrchestrator()
