"""Price context analysis service for market comparison."""

from typing import Dict, Any, List, Optional, Tuple
import structlog
from datetime import datetime, timedelta
from collections import defaultdict

logger = structlog.get_logger()


class PriceContextService:
    """
    Analyze price context by comparing listing prices to market data.

    Calculates:
    - Price percentile within district/building type
    - Price per square meter comparison
    - Price trends (if historical data available)
    - Value assessment (deal/fair/expensive)

    Uses internal database for market statistics.
    """

    # Cache market stats for 1 day
    CACHE_TTL_HOURS = 24

    def __init__(self):
        """Initialize price context service."""
        self._market_cache: Dict[str, Dict[str, Any]] = {}
        self._last_cache_update: Dict[str, datetime] = {}
        logger.info("price_context_service_initialized")

    async def analyze_listing_price(
        self,
        listing_id: str,
        price: float,
        area_total: float,
        rooms: int,
        district: str,
        building_type: Optional[str] = None,
        renovation: Optional[str] = None,
        all_listings: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Analyze listing price in market context.

        Args:
            listing_id: Listing ID
            price: Listing price
            area_total: Total area in m²
            rooms: Number of rooms
            district: District name
            building_type: Building type
            renovation: Renovation type
            all_listings: All active listings for comparison (optional)

        Returns:
            Price context dictionary:
            {
                "price_per_sqm": float,
                "price_percentile": float,  # 0-100
                "district_avg_price": float,
                "district_median_price": float,
                "value_assessment": str,  # "deal"/"fair"/"expensive"
                "comparable_count": int,
                "price_vs_avg": float,  # Percentage difference
                "context": str,  # Human-readable explanation
                "analyzed_at": str
            }
        """
        logger.info("analyzing_price_context",
                   listing_id=listing_id,
                   price=price,
                   district=district)

        try:
            # Calculate price per sqm
            price_per_sqm = price / area_total if area_total > 0 else 0

            # Get market statistics
            market_stats = await self._get_market_stats(
                district=district,
                rooms=rooms,
                building_type=building_type,
                renovation=renovation,
                all_listings=all_listings
            )

            # Calculate percentile
            percentile = self._calculate_percentile(
                price=price,
                market_prices=market_stats["prices"]
            )

            # Assess value
            value_assessment = self._assess_value(
                price=price,
                avg_price=market_stats["avg_price"],
                percentile=percentile
            )

            # Calculate price vs average
            price_vs_avg = 0.0
            if market_stats["avg_price"] > 0:
                price_vs_avg = ((price - market_stats["avg_price"]) / market_stats["avg_price"]) * 100

            # Generate context explanation
            context = self._generate_context_explanation(
                price=price,
                price_per_sqm=price_per_sqm,
                percentile=percentile,
                value_assessment=value_assessment,
                market_stats=market_stats
            )

            price_context = {
                "price_per_sqm": round(price_per_sqm, 0),
                "price_percentile": round(percentile, 1),
                "district_avg_price": market_stats["avg_price"],
                "district_median_price": market_stats["median_price"],
                "district_avg_price_per_sqm": market_stats["avg_price_per_sqm"],
                "value_assessment": value_assessment,
                "comparable_count": market_stats["count"],
                "price_vs_avg": round(price_vs_avg, 1),
                "context": context,
                "analyzed_at": datetime.utcnow().isoformat()
            }

            logger.info("price_context_analyzed",
                       listing_id=listing_id,
                       percentile=percentile,
                       value=value_assessment)

            return price_context

        except Exception as e:
            logger.error("price_context_error",
                        listing_id=listing_id,
                        error=str(e))
            return self._empty_price_context()

    async def _get_market_stats(
        self,
        district: str,
        rooms: int,
        building_type: Optional[str] = None,
        renovation: Optional[str] = None,
        all_listings: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Get market statistics for comparison.

        Args:
            district: District name
            rooms: Number of rooms
            building_type: Building type filter
            renovation: Renovation filter
            all_listings: All listings to analyze

        Returns:
            Market statistics
        """
        # Build cache key
        cache_key = f"{district}_{rooms}_{building_type}_{renovation}"

        # Check cache
        if cache_key in self._market_cache:
            last_update = self._last_cache_update.get(cache_key)
            if last_update and datetime.utcnow() - last_update < timedelta(hours=self.CACHE_TTL_HOURS):
                logger.debug("market_stats_cache_hit", cache_key=cache_key)
                return self._market_cache[cache_key]

        # Filter comparable listings
        if all_listings:
            comparable = self._filter_comparable_listings(
                all_listings=all_listings,
                district=district,
                rooms=rooms,
                building_type=building_type,
                renovation=renovation
            )
        else:
            # If no listings provided, return empty stats
            comparable = []

        # Calculate statistics
        if not comparable:
            stats = {
                "count": 0,
                "avg_price": 0,
                "median_price": 0,
                "avg_price_per_sqm": 0,
                "prices": [],
                "prices_per_sqm": []
            }
        else:
            prices = [l["price"] for l in comparable if l.get("price")]
            prices_per_sqm = [
                l["price"] / l["area_total"]
                for l in comparable
                if l.get("price") and l.get("area_total") and l["area_total"] > 0
            ]

            stats = {
                "count": len(comparable),
                "avg_price": sum(prices) / len(prices) if prices else 0,
                "median_price": self._median(prices) if prices else 0,
                "avg_price_per_sqm": sum(prices_per_sqm) / len(prices_per_sqm) if prices_per_sqm else 0,
                "prices": sorted(prices),
                "prices_per_sqm": sorted(prices_per_sqm)
            }

        # Cache results
        self._market_cache[cache_key] = stats
        self._last_cache_update[cache_key] = datetime.utcnow()

        logger.debug("market_stats_calculated",
                    cache_key=cache_key,
                    comparable_count=stats["count"])

        return stats

    def _filter_comparable_listings(
        self,
        all_listings: List[Dict[str, Any]],
        district: str,
        rooms: int,
        building_type: Optional[str] = None,
        renovation: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter listings for comparison.

        Args:
            all_listings: All listings
            district: District to match
            rooms: Number of rooms to match
            building_type: Building type to match (optional)
            renovation: Renovation to match (optional)

        Returns:
            Filtered comparable listings
        """
        comparable = []

        for listing in all_listings:
            # Must match district and rooms
            if listing.get("district") != district:
                continue

            if listing.get("rooms") != rooms:
                continue

            # Optional filters
            if building_type and listing.get("building_type") != building_type:
                continue

            if renovation and listing.get("renovation") != renovation:
                continue

            # Must have price and area
            if not listing.get("price") or not listing.get("area_total"):
                continue

            comparable.append(listing)

        return comparable

    def _calculate_percentile(
        self,
        price: float,
        market_prices: List[float]
    ) -> float:
        """
        Calculate price percentile in market.

        Args:
            price: Listing price
            market_prices: Sorted list of market prices

        Returns:
            Percentile (0-100)
        """
        if not market_prices:
            return 50.0  # Default to median

        # Count prices below this price
        below_count = sum(1 for p in market_prices if p < price)

        # Calculate percentile
        percentile = (below_count / len(market_prices)) * 100

        return percentile

    def _assess_value(
        self,
        price: float,
        avg_price: float,
        percentile: float
    ) -> str:
        """
        Assess value (deal/fair/expensive).

        Args:
            price: Listing price
            avg_price: Average market price
            percentile: Price percentile

        Returns:
            Value assessment string
        """
        if percentile < 25:
            return "deal"  # Bottom 25% - great deal
        elif percentile < 40:
            return "good_value"  # 25-40% - good value
        elif percentile <= 60:
            return "fair"  # 40-60% - fair price
        elif percentile <= 75:
            return "above_average"  # 60-75% - above average
        else:
            return "expensive"  # Top 25% - expensive

    def _generate_context_explanation(
        self,
        price: float,
        price_per_sqm: float,
        percentile: float,
        value_assessment: str,
        market_stats: Dict[str, Any]
    ) -> str:
        """
        Generate human-readable context explanation.

        Args:
            price: Listing price
            price_per_sqm: Price per square meter
            percentile: Price percentile
            value_assessment: Value assessment
            market_stats: Market statistics

        Returns:
            Human-readable explanation in Russian
        """
        parts = []

        # Value assessment
        value_texts = {
            "deal": f"💰 Отличная цена! В нижних 25% рынка (перцентиль {percentile:.0f})",
            "good_value": f"✅ Хорошая цена (перцентиль {percentile:.0f})",
            "fair": f"⚖️ Рыночная цена (перцентиль {percentile:.0f})",
            "above_average": f"📊 Выше среднего (перцентиль {percentile:.0f})",
            "expensive": f"💸 Высокая цена (перцентиль {percentile:.0f}, топ-25%)"
        }
        parts.append(value_texts.get(value_assessment, ""))

        # Price comparison
        avg_price = market_stats["avg_price"]
        if avg_price > 0:
            diff_pct = ((price - avg_price) / avg_price) * 100

            if abs(diff_pct) < 5:
                parts.append(f"Соответствует средней цене района")
            elif diff_pct < -10:
                parts.append(f"На {abs(diff_pct):.0f}% ниже средней - возможен торг")
            elif diff_pct > 10:
                parts.append(f"На {diff_pct:.0f}% выше средней")

        # Price per sqm comparison
        avg_per_sqm = market_stats["avg_price_per_sqm"]
        if avg_per_sqm > 0:
            parts.append(f"Цена за м²: {price_per_sqm:,.0f} руб (среднее: {avg_per_sqm:,.0f} руб)")

        # Sample size
        count = market_stats["count"]
        if count > 0:
            parts.append(f"Сравнение с {count} аналогичными объектами")
        else:
            parts.append("⚠️ Недостаточно данных для сравнения")

        return ". ".join(parts)

    def _median(self, numbers: List[float]) -> float:
        """Calculate median of list."""
        if not numbers:
            return 0.0

        sorted_numbers = sorted(numbers)
        n = len(sorted_numbers)

        if n % 2 == 0:
            return (sorted_numbers[n // 2 - 1] + sorted_numbers[n // 2]) / 2
        else:
            return sorted_numbers[n // 2]

    def _empty_price_context(self) -> Dict[str, Any]:
        """Return empty price context structure."""
        return {
            "price_per_sqm": None,
            "price_percentile": None,
            "district_avg_price": None,
            "district_median_price": None,
            "district_avg_price_per_sqm": None,
            "value_assessment": None,
            "comparable_count": 0,
            "price_vs_avg": None,
            "context": "Недостаточно данных для анализа",
            "analyzed_at": datetime.utcnow().isoformat()
        }

    def get_price_summary(self, price_context: Dict[str, Any]) -> str:
        """
        Generate human-readable price summary.

        Args:
            price_context: Price context from analyze_listing_price()

        Returns:
            Human-readable summary in Russian
        """
        return price_context.get("context", "Анализ цены: данные недоступны")


# Global instance
price_context_service = PriceContextService()
