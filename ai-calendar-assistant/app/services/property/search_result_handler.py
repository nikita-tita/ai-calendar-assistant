"""Search result handler - manages different result scenarios."""

from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import structlog

from app.schemas.property import PropertyListingResponse, PropertyClientResponse

logger = structlog.get_logger()


class SearchResultHandler:
    """
    Handles different search result scenarios and provides smart strategies.

    Scenarios:
    1. No results (0) - Smart filter relaxation
    2. Few results (1-20) - Show all + expansion suggestions
    3. Optimal results (20-200) - Ranking + top results
    4. Too many results (200+) - Smart narrowing
    5. Clustered results (100+ in one complex) - Group by layout
    """

    @staticmethod
    async def handle_results(
        listings: List[PropertyListingResponse],
        client: PropertyClientResponse,
        filters_used: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main entry point - route to appropriate handler based on result count.

        Args:
            listings: Search results
            client: Client preferences
            filters_used: Dictionary of filters that were applied

        Returns:
            Dictionary with:
            - scenario: str (no_results, few, optimal, too_many, clustered)
            - listings: List of listings to show
            - message: str - Message to user
            - suggestions: List[Dict] - Next steps
            - stats: Dict - Result statistics
        """
        count = len(listings)

        logger.info("handling_search_results",
                   count=count,
                   client_id=client.id,
                   filters_count=len(filters_used))

        # Route to appropriate handler
        if count == 0:
            return await SearchResultHandler.handle_no_results(client, filters_used)

        elif count <= 20:
            return await SearchResultHandler.handle_few_results(listings, client, filters_used)

        elif count <= 200:
            return await SearchResultHandler.handle_optimal_results(listings, client, filters_used)

        else:
            # Check if clustered in one complex
            complex_counts = SearchResultHandler._count_by_complex(listings)
            max_complex_count = max(complex_counts.values()) if complex_counts else 0

            if max_complex_count >= 100:
                return await SearchResultHandler.handle_clustered_results(listings, client, filters_used)
            else:
                return await SearchResultHandler.handle_too_many_results(listings, client, filters_used)

    @staticmethod
    async def handle_no_results(
        client: PropertyClientResponse,
        filters_used: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle zero results - suggest smart filter relaxation.

        Strategy:
        1. Identify which filters are most restrictive
        2. Suggest relaxing them in priority order:
           - Financial conditions (mortgage, payment methods)
           - Layout details (balcony type, bathroom type)
           - Building specifics (building type, renovation)
           - Handover date (quarter/year)
           - Core parameters (price, rooms, area) - LAST resort

        Returns:
            Scenario data with relaxation suggestions
        """
        logger.info("handling_no_results", client_id=client.id, filters_count=len(filters_used))

        # Prioritized relaxation suggestions
        suggestions = []

        # Check financial filters
        if filters_used.get("mortgage_required"):
            suggestions.append({
                "type": "relax_mortgage",
                "message": "Попробуйте убрать требование ипотеки - возможно есть объекты с другими способами оплаты",
                "filter": "mortgage_required"
            })

        if filters_used.get("payment_methods"):
            suggestions.append({
                "type": "relax_payment_methods",
                "message": "Расширьте способы оплаты - могут быть интересные варианты",
                "filter": "payment_methods"
            })

        # Check layout filters
        if filters_used.get("balcony_required"):
            suggestions.append({
                "type": "relax_balcony",
                "message": "Попробуйте без требования балкона",
                "filter": "balcony_required"
            })

        if filters_used.get("bathroom_type"):
            suggestions.append({
                "type": "relax_bathroom",
                "message": "Рассмотрите оба типа санузлов (раздельный и совмещенный)",
                "filter": "bathroom_type"
            })

        # Check building filters
        if filters_used.get("building_types"):
            suggestions.append({
                "type": "relax_building_type",
                "message": "Расширьте типы домов - современные панельные дома могут быть очень качественными",
                "filter": "building_types"
            })

        if filters_used.get("renovations"):
            suggestions.append({
                "type": "relax_renovation",
                "message": "Рассмотрите другие варианты отделки",
                "filter": "renovations"
            })

        # Check handover date
        if filters_used.get("handover_year_min") or filters_used.get("handover_quarter_min"):
            suggestions.append({
                "type": "relax_handover_date",
                "message": "Расширьте сроки сдачи - могут быть объекты чуть позже",
                "filter": "handover_date"
            })

        # Check developer
        if filters_used.get("developers"):
            suggestions.append({
                "type": "relax_developers",
                "message": "Попробуйте других застройщиков",
                "filter": "developers"
            })

        # Last resort - core parameters
        if filters_used.get("price_max"):
            price_increase = int(filters_used["price_max"] * 0.1)  # 10% increase
            suggestions.append({
                "type": "increase_budget",
                "message": f"Увеличьте бюджет на {price_increase:,} руб (+10%) - это откроет новые варианты",
                "filter": "price_max",
                "new_value": filters_used["price_max"] + price_increase
            })

        if filters_used.get("rooms_max"):
            suggestions.append({
                "type": "expand_rooms",
                "message": "Рассмотрите квартиры с другим количеством комнат",
                "filter": "rooms"
            })

        if filters_used.get("districts"):
            suggestions.append({
                "type": "expand_districts",
                "message": "Расширьте районы поиска - соседние районы могут быть интересны",
                "filter": "districts"
            })

        return {
            "scenario": "no_results",
            "listings": [],
            "message": "К сожалению, по вашим критериям ничего не найдено.",
            "suggestions": suggestions[:3],  # Top 3 suggestions
            "stats": {
                "total": 0,
                "filters_applied": len(filters_used)
            }
        }

    @staticmethod
    async def handle_few_results(
        listings: List[PropertyListingResponse],
        client: PropertyClientResponse,
        filters_used: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle few results (1-20) - show all + suggest expansion.

        Strategy:
        1. Show all results ranked by score
        2. Suggest expanding search slightly
        3. Explain why these are the only matches

        Returns:
            Scenario data with all listings
        """
        count = len(listings)
        logger.info("handling_few_results", count=count, client_id=client.id)

        # Simple ranking (can be enhanced with scoring later)
        ranked_listings = sorted(listings, key=lambda x: x.price)

        # Generate expansion suggestions
        suggestions = []

        if filters_used.get("districts") and len(filters_used["districts"]) < 3:
            suggestions.append({
                "type": "expand_districts",
                "message": "Расширьте районы поиска для большего выбора"
            })

        if filters_used.get("price_max"):
            price_increase = int(filters_used["price_max"] * 0.05)  # 5% increase
            suggestions.append({
                "type": "increase_budget",
                "message": f"Увеличьте бюджет на {price_increase:,} руб - появятся новые варианты"
            })

        if filters_used.get("renovations"):
            suggestions.append({
                "type": "relax_renovation",
                "message": "Рассмотрите другие типы отделки"
            })

        message = f"Нашёл {count} {'вариант' if count == 1 else 'варианта' if count < 5 else 'вариантов'}"

        return {
            "scenario": "few_results",
            "listings": ranked_listings,
            "message": message,
            "suggestions": suggestions[:2],
            "stats": {
                "total": count,
                "price_range": f"{min(l.price for l in listings):,} - {max(l.price for l in listings):,} руб",
                "avg_price": int(sum(l.price for l in listings) / count)
            }
        }

    @staticmethod
    async def handle_optimal_results(
        listings: List[PropertyListingResponse],
        client: PropertyClientResponse,
        filters_used: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle optimal results (20-200) - rank and show top.

        Strategy:
        1. Rank all results by dream score (or simple scoring)
        2. Show top 12
        3. Provide statistics
        4. Offer to narrow if needed

        Returns:
            Scenario data with top ranked listings
        """
        count = len(listings)
        logger.info("handling_optimal_results", count=count, client_id=client.id)

        # Simple ranking by price (can be enhanced with dream score)
        ranked_listings = sorted(listings, key=lambda x: x.price)

        # Show top 12
        top_listings = ranked_listings[:12]

        # Generate statistics
        prices = [l.price for l in listings]
        areas = [l.area_total for l in listings if l.area_total]

        stats = {
            "total": count,
            "showing": len(top_listings),
            "price_min": min(prices),
            "price_max": max(prices),
            "price_avg": int(sum(prices) / len(prices)),
            "area_min": min(areas) if areas else None,
            "area_max": max(areas) if areas else None,
            "area_avg": round(sum(areas) / len(areas), 1) if areas else None
        }

        # Suggest narrowing if count > 100
        suggestions = []
        if count > 100:
            # Check what filters are NOT yet applied
            if not filters_used.get("renovations"):
                suggestions.append({
                    "type": "add_renovation",
                    "message": "Уточните тип отделки для сужения выбора"
                })

            if not filters_used.get("building_types"):
                suggestions.append({
                    "type": "add_building_type",
                    "message": "Укажите предпочтительный тип дома"
                })

            if not filters_used.get("handover_year_min"):
                suggestions.append({
                    "type": "add_handover_date",
                    "message": "Уточните желаемый срок сдачи"
                })

        message = f"Нашёл {count} вариантов. Показываю топ-{len(top_listings)} по цене."

        return {
            "scenario": "optimal_results",
            "listings": top_listings,
            "message": message,
            "suggestions": suggestions[:2],
            "stats": stats
        }

    @staticmethod
    async def handle_too_many_results(
        listings: List[PropertyListingResponse],
        client: PropertyClientResponse,
        filters_used: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle too many results (200+) - smart narrowing required.

        Strategy:
        1. Identify missing critical filters
        2. Ask prioritized questions:
           - Building/Complex selection (if 15+ buildings)
           - Renovation type
           - Handover date
           - Building type
           - Floor preferences
        3. Show top 12 as preview

        Returns:
            Scenario data with narrowing questions
        """
        count = len(listings)
        logger.info("handling_too_many_results", count=count, client_id=client.id)

        # Analyze listings to suggest best narrowing strategy
        buildings = defaultdict(int)
        renovations = defaultdict(int)
        building_types = defaultdict(int)

        for listing in listings:
            if listing.building_name:
                buildings[listing.building_name] += 1
            if listing.renovation:
                renovations[listing.renovation] += 1
            if listing.building_type:
                building_types[listing.building_type] += 1

        # Prioritized narrowing suggestions
        suggestions = []

        # 1. Building selection (most effective if 15+ buildings)
        if len(buildings) >= 15:
            top_buildings = sorted(buildings.items(), key=lambda x: x[1], reverse=True)[:5]
            suggestions.append({
                "type": "select_building",
                "priority": 1,
                "message": f"Найдено {len(buildings)} ЖК. Уточните какой комплекс вас интересует?",
                "options": [{"name": name, "count": count} for name, count in top_buildings],
                "filter": "building_name"
            })

        # 2. Renovation type (if not specified)
        if not filters_used.get("renovations") and len(renovations) > 1:
            suggestions.append({
                "type": "select_renovation",
                "priority": 2,
                "message": "Какой тип отделки вас интересует?",
                "options": [{"name": name, "count": count} for name, count in renovations.items()],
                "filter": "renovations"
            })

        # 3. Handover date (if not specified)
        if not filters_used.get("handover_year_min"):
            suggestions.append({
                "type": "select_handover_date",
                "priority": 3,
                "message": "Когда вам нужна квартира? Укажите желаемый квартал и год сдачи",
                "filter": "handover_date"
            })

        # 4. Building type (if not specified and diverse)
        if not filters_used.get("building_types") and len(building_types) > 2:
            suggestions.append({
                "type": "select_building_type",
                "priority": 4,
                "message": "Какой тип дома предпочитаете?",
                "options": [{"name": name, "count": count} for name, count in building_types.items()],
                "filter": "building_types"
            })

        # 5. Floor preferences (if not specified)
        if not filters_used.get("floor_min") and not filters_used.get("floor_max"):
            suggestions.append({
                "type": "select_floor",
                "priority": 5,
                "message": "Есть ли предпочтения по этажу?",
                "filter": "floor"
            })

        # Sort by priority
        suggestions.sort(key=lambda x: x["priority"])

        # Show preview - top 12 by price
        preview_listings = sorted(listings, key=lambda x: x.price)[:12]

        message = f"Найдено {count} вариантов - это слишком много. Нужно уточнить критерии."

        return {
            "scenario": "too_many_results",
            "listings": preview_listings,
            "message": message,
            "suggestions": suggestions[:3],  # Top 3 questions
            "stats": {
                "total": count,
                "buildings_count": len(buildings),
                "renovations_available": list(renovations.keys()),
                "building_types_available": list(building_types.keys())
            }
        }

    @staticmethod
    async def handle_clustered_results(
        listings: List[PropertyListingResponse],
        client: PropertyClientResponse,
        filters_used: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle clustered results (100+ in one complex) - group by layout.

        Strategy:
        1. Identify dominant complex
        2. Cluster by layout: (rooms, area_range, balcony_type, bathroom_type)
        3. Show representative from each cluster
        4. User selects preferred layout
        5. Then show all variants of that layout

        Returns:
            Scenario data with layout clusters
        """
        count = len(listings)
        logger.info("handling_clustered_results", count=count, client_id=client.id)

        # Group by building
        by_building = defaultdict(list)
        for listing in listings:
            key = listing.building_name or "unknown"
            by_building[key].append(listing)

        # Find dominant building
        dominant_building = max(by_building.items(), key=lambda x: len(x[1]))
        building_name, building_listings = dominant_building

        # Cluster by layout
        clusters = SearchResultHandler._cluster_by_layout(building_listings)

        # Create cluster summaries
        cluster_summaries = []
        for cluster_id, cluster_listings in clusters.items():
            representative = cluster_listings[0]
            prices = [l.price for l in cluster_listings]

            cluster_summaries.append({
                "cluster_id": cluster_id,
                "count": len(cluster_listings),
                "representative": representative,
                "price_min": min(prices),
                "price_max": max(prices),
                "price_avg": int(sum(prices) / len(prices)),
                "description": SearchResultHandler._describe_layout(representative)
            })

        # Sort by price
        cluster_summaries.sort(key=lambda x: x["price_avg"])

        message = f"В ЖК '{building_name}' найдено {len(building_listings)} вариантов. Сгруппировал по планировкам."

        return {
            "scenario": "clustered_results",
            "listings": [c["representative"] for c in cluster_summaries],
            "message": message,
            "clusters": cluster_summaries,
            "suggestions": [{
                "type": "select_layout",
                "message": "Выберите понравившуюся планировку, покажу все варианты"
            }],
            "stats": {
                "total": count,
                "building": building_name,
                "layouts_count": len(clusters),
                "in_dominant_building": len(building_listings)
            }
        }

    @staticmethod
    def _count_by_complex(listings: List[PropertyListingResponse]) -> Dict[str, int]:
        """Count listings by complex/building."""
        counts = defaultdict(int)
        for listing in listings:
            key = listing.building_name or "unknown"
            counts[key] += 1
        return counts

    @staticmethod
    def _cluster_by_layout(listings: List[PropertyListingResponse]) -> Dict[str, List[PropertyListingResponse]]:
        """
        Cluster listings by layout characteristics.

        Cluster key: (rooms, area_range, balcony_type, bathroom_type)
        Area ranges: <40, 40-60, 60-80, 80-100, 100+
        """
        clusters = defaultdict(list)

        for listing in listings:
            # Determine area range
            area = listing.area_total or 0
            if area < 40:
                area_range = "<40"
            elif area < 60:
                area_range = "40-60"
            elif area < 80:
                area_range = "60-80"
            elif area < 100:
                area_range = "80-100"
            else:
                area_range = "100+"

            # Create cluster key
            key = (
                listing.rooms or 0,
                area_range,
                listing.balcony_type or "none",
                listing.bathroom_type or "unknown"
            )

            clusters[str(key)] = listing

        return clusters

    @staticmethod
    def _describe_layout(listing: PropertyListingResponse) -> str:
        """Generate human-readable layout description."""
        parts = []

        if listing.rooms:
            parts.append(f"{listing.rooms}-комн")

        if listing.area_total:
            parts.append(f"{listing.area_total} м²")

        if listing.balcony_type:
            parts.append(f"балкон: {listing.balcony_type}")

        if listing.bathroom_type:
            parts.append(f"санузел: {listing.bathroom_type}")

        return ", ".join(parts) if parts else "планировка не указана"


# Global instance
search_result_handler = SearchResultHandler()
