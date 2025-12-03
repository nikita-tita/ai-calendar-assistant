"""Property scoring and ranking system."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


@dataclass
class ScoringWeights:
    """Default scoring weights for Dream Score calculation."""
    location: float = 0.35  # Location and proximity to anchor points
    transport: float = 0.15  # Public transport accessibility
    light: float = 0.10  # Natural light and views
    view: float = 0.05  # View quality
    plan: float = 0.10  # Layout and planning
    noise: float = 0.05  # Noise level
    infra: float = 0.10  # Infrastructure (POIs)
    price: float = 0.20  # Price context and value
    building: float = 0.05  # Building quality and developer reputation


class PropertyScoringService:
    """Service for scoring and ranking properties."""

    def __init__(self):
        """Initialize scoring service."""
        self.default_weights = ScoringWeights()

    def calculate_dream_score(
        self,
        listing: Dict[str, Any],
        client_profile: Dict[str, Any],
        weights: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Calculate Dream Score for a listing based on client profile.

        Args:
            listing: Property listing data
            client_profile: Client preferences and requirements
            weights: Optional custom weights (overrides defaults)

        Returns:
            Dream score (0-100)
        """
        # Use custom weights or defaults
        if weights:
            w = self._parse_weights(weights)
        else:
            w = self.default_weights

        # Calculate component scores
        location_score = self._score_location(listing, client_profile)
        transport_score = self._score_transport(listing, client_profile)
        light_score = self._score_light(listing)
        view_score = self._score_view(listing)
        plan_score = self._score_plan(listing, client_profile)
        noise_score = self._score_noise(listing)
        infra_score = self._score_infrastructure(listing, client_profile)
        price_score = self._score_price_context(listing, client_profile)
        building_score = self._score_building(listing)

        # Weighted sum
        dream_score = (
            w.location * location_score +
            w.transport * transport_score +
            w.light * light_score +
            w.view * view_score +
            w.plan * plan_score +
            w.noise * noise_score +
            w.infra * infra_score +
            w.price * price_score +
            w.building * building_score
        ) * 100  # Scale to 0-100

        logger.debug("dream_score_calculated",
                    listing_id=listing.get("id"),
                    score=dream_score,
                    components={
                        "location": location_score,
                        "transport": transport_score,
                        "price": price_score
                    })

        return round(dream_score, 2)

    def _score_location(self, listing: Dict[str, Any], client_profile: Dict[str, Any]) -> float:
        """Score based on location and distance to anchor points."""
        score = 0.5  # Base score

        # Check if in preferred districts
        districts = client_profile.get("districts", [])
        if districts and listing.get("district") in districts:
            score += 0.3

        # Calculate distance to anchor points
        anchor_points = client_profile.get("anchor_points", [])
        if anchor_points and listing.get("routes_cache"):
            routes = listing["routes_cache"].get(client_profile.get("id"), {})

            # Average route time score (closer is better)
            route_scores = []
            for point in anchor_points:
                point_type = point.get("type")
                mode = point.get("mode", "auto")
                route_key = f"to_{point_type}"

                if route_key in routes and mode in routes[route_key]:
                    time_minutes = routes[route_key][mode]
                    # Score: 1.0 for <15 min, 0.5 for 30 min, 0.0 for >60 min
                    if time_minutes <= 15:
                        route_scores.append(1.0)
                    elif time_minutes <= 30:
                        route_scores.append(0.7)
                    elif time_minutes <= 45:
                        route_scores.append(0.4)
                    elif time_minutes <= 60:
                        route_scores.append(0.2)
                    else:
                        route_scores.append(0.0)

            if route_scores:
                score += 0.2 * (sum(route_scores) / len(route_scores))

        return min(score, 1.0)

    def _score_transport(self, listing: Dict[str, Any], client_profile: Dict[str, Any]) -> float:
        """Score based on public transport accessibility."""
        score = 0.3  # Base score

        metro_distance = listing.get("metro_distance_minutes")
        max_distance = client_profile.get("max_metro_distance_minutes", 15)

        if metro_distance is not None:
            if metro_distance <= 5:
                score += 0.7
            elif metro_distance <= 10:
                score += 0.5
            elif metro_distance <= max_distance:
                score += 0.3
            elif metro_distance <= max_distance * 1.5:
                score += 0.1

        return min(score, 1.0)

    def _score_light(self, listing: Dict[str, Any]) -> float:
        """Score based on natural light (from vision data)."""
        vision_data = listing.get("vision_data") or {}
        light_score = vision_data.get("light_score", 0.5) if isinstance(vision_data, dict) else 0.5
        return min(light_score, 1.0)

    def _score_view(self, listing: Dict[str, Any]) -> float:
        """Score based on view quality (from vision data)."""
        vision_data = listing.get("vision_data") or {}
        view_tags = vision_data.get("view_tags", [])

        score = 0.3  # Base score

        # Positive view tags
        positive_tags = ["park", "quiet", "green", "panoramic", "river", "courtyard"]
        negative_tags = ["street", "noisy", "construction"]

        for tag in view_tags:
            if tag in positive_tags:
                score += 0.15
            elif tag in negative_tags:
                score -= 0.1

        return max(0.0, min(score, 1.0))

    def _score_plan(self, listing: Dict[str, Any], client_profile: Dict[str, Any]) -> float:
        """Score based on layout and planning."""
        score = 0.5  # Base score

        amenities = listing.get("amenities") or {}

        # Check for desirable amenities
        if amenities.get("balcony"):
            score += 0.15
        if amenities.get("storage"):
            score += 0.10
        if amenities.get("walk_in_closet"):
            score += 0.10

        # Check rooms match
        rooms = listing.get("rooms", 0)
        rooms_min = client_profile.get("rooms_min", 1)
        rooms_max = client_profile.get("rooms_max", 5)

        if rooms_min <= rooms <= rooms_max:
            score += 0.15

        return min(score, 1.0)

    def _score_noise(self, listing: Dict[str, Any]) -> float:
        """Score based on noise level (from vision data and location)."""
        vision_data = listing.get("vision_data") or {}
        view_tags = vision_data.get("view_tags", [])

        score = 0.6  # Base score

        if "courtyard" in view_tags or "quiet" in view_tags:
            score += 0.3
        if "street" in view_tags or "noisy" in view_tags:
            score -= 0.3

        return max(0.0, min(score, 1.0))

    def _score_infrastructure(self, listing: Dict[str, Any], client_profile: Dict[str, Any]) -> float:
        """Score based on nearby infrastructure (POI data)."""
        score = 0.2  # Base score

        poi_data = listing.get("poi_data") or {}

        # Check essential POIs
        if poi_data.get("grocery_500m", 0) > 0:
            score += 0.2
        if poi_data.get("school_1km", 0) > 0 and client_profile.get("allows_kids"):
            score += 0.15
        if poi_data.get("kindergarten_1km", 0) > 0 and client_profile.get("allows_kids"):
            score += 0.15
        if poi_data.get("park_1km", 0) > 0:
            score += 0.15
        if poi_data.get("sport_1km", 0) > 0:
            score += 0.10
        if poi_data.get("pharmacy_500m", 0) > 0:
            score += 0.05

        return min(score, 1.0)

    def _score_price_context(self, listing: Dict[str, Any], client_profile: Dict[str, Any]) -> float:
        """Score based on price context (value for money)."""
        score = 0.3  # Base score

        price = listing.get("price", 0)
        budget_min = client_profile.get("budget_min") or 0
        budget_max = client_profile.get("budget_max") or float('inf')

        # Check if within budget (handle None values)
        if budget_min is None:
            budget_min = 0
        if budget_max is None:
            budget_max = float('inf')

        if not (budget_min <= price <= budget_max):
            return 0.0

        # Get market data
        market_data = listing.get("market_data") or {}
        median = market_data.get("median", price)
        pct = market_data.get("pct", 50)

        # Score based on price position
        if pct <= 40:  # Below market
            score += 0.5
        elif pct <= 60:  # At market
            score += 0.3
        elif pct <= 75:  # Slightly above
            score += 0.1
        # else: above market, no bonus

        # Bonus for being in optimal budget range
        budget_mid = (budget_min + budget_max) / 2
        price_distance = abs(price - budget_mid) / (budget_max - budget_min) if budget_max > budget_min else 0

        if price_distance < 0.2:  # Within 20% of mid-point
            score += 0.2

        return min(score, 1.0)

    def _score_building(self, listing: Dict[str, Any]) -> float:
        """Score based on building quality and developer."""
        score = 0.5  # Base score

        builder_data = listing.get("builder_data") or {}
        risk_score = builder_data.get("risk_score", 0.5)

        # Lower risk = higher score
        score += (1.0 - risk_score) * 0.3

        # Check elevator for multi-story buildings
        floors_total = listing.get("floors_total", 1)
        floor = listing.get("floor", 1)
        amenities = listing.get("amenities") or {}

        if floors_total > 4 and floor > 2 and amenities.get("elevator"):
            score += 0.2

        return min(score, 1.0)

    def _parse_weights(self, weights_dict: Dict[str, float]) -> ScoringWeights:
        """Parse custom weights dictionary into ScoringWeights object."""
        return ScoringWeights(
            location=weights_dict.get("location", self.default_weights.location),
            transport=weights_dict.get("transport", self.default_weights.transport),
            light=weights_dict.get("light", self.default_weights.light),
            view=weights_dict.get("view", self.default_weights.view),
            plan=weights_dict.get("plan", self.default_weights.plan),
            noise=weights_dict.get("noise", self.default_weights.noise),
            infra=weights_dict.get("infra", self.default_weights.infra),
            price=weights_dict.get("price", self.default_weights.price),
            building=weights_dict.get("building", self.default_weights.building),
        )

    def rank_listings(
        self,
        listings: List[Dict[str, Any]],
        client_profile: Dict[str, Any],
        weights: Optional[Dict[str, float]] = None,
        top_n: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Rank listings by Dream Score and return top N.

        Args:
            listings: List of property listings
            client_profile: Client preferences
            weights: Optional custom weights
            top_n: Number of top results to return

        Returns:
            List of listings with dream_score added, sorted by score
        """
        # Calculate scores for all listings
        scored_listings = []
        for listing in listings:
            dream_score = self.calculate_dream_score(listing, client_profile, weights)
            listing_copy = listing.copy()
            listing_copy["dream_score"] = dream_score
            scored_listings.append(listing_copy)

        # Sort by dream_score descending
        scored_listings.sort(key=lambda x: x["dream_score"], reverse=True)

        # Return top N
        top_listings = scored_listings[:top_n]

        # Add rank
        for i, listing in enumerate(top_listings, 1):
            listing["rank"] = i

        logger.info("listings_ranked",
                   total=len(listings),
                   top_n=len(top_listings),
                   top_score=top_listings[0]["dream_score"] if top_listings else 0)

        return top_listings

    def generate_explanation(
        self,
        listing: Dict[str, Any],
        client_profile: Dict[str, Any],
        dream_score: float
    ) -> Dict[str, Any]:
        """
        Generate human-readable explanation for why listing was selected.

        Args:
            listing: Property listing
            client_profile: Client profile
            dream_score: Calculated dream score

        Returns:
            Explanation dictionary
        """
        explanation = {
            "why_top": [],
            "compromise": [],
            "price_context": "",
            "routes": {},
            "check_on_viewing": []
        }

        # Why in top
        if listing.get("metro_distance_minutes", 100) <= 10:
            explanation["why_top"].append(f"Близко к метро ({listing['metro_distance_minutes']} мин)")

        vision_data = listing.get("vision_data") or {}
        if vision_data.get("light_score", 0) > 0.7:
            explanation["why_top"].append("Светлая квартира с хорошим освещением")

        if "courtyard" in vision_data.get("view_tags", []):
            explanation["why_top"].append("Тихий двор")

        poi_data = listing.get("poi_data") or {}
        if poi_data.get("park_1km", 0) > 0:
            explanation["why_top"].append("Рядом парк для прогулок")

        # Compromises
        floor = listing.get("floor", 1)
        if floor == 1 and client_profile.get("not_first_floor"):
            explanation["compromise"].append("Первый этаж")

        if floor == listing.get("floors_total") and client_profile.get("not_last_floor"):
            explanation["compromise"].append("Последний этаж")

        amenities = listing.get("amenities") or {}
        if not amenities.get("elevator") and floor > 3:
            explanation["compromise"].append(f"{floor} этаж без лифта")

        # Price context
        market_data = listing.get("market_data") or {}
        pct = market_data.get("pct", 50)
        if pct < 40:
            explanation["price_context"] = f"Цена ниже рынка на {50-pct}%. Хороший вариант для торга."
        elif pct > 60:
            explanation["price_context"] = f"Цена выше рынка на {pct-50}%. Есть пространство для переговоров."
        else:
            explanation["price_context"] = "Цена соответствует рынку."

        # Routes
        routes_cache = listing.get("routes_cache") or {}
        client_routes = routes_cache.get(client_profile.get("id"), {})

        for route_key, times in client_routes.items():
            route_name = route_key.replace("to_", "До ")
            explanation["routes"][route_name] = times

        # What to check
        if floor == 1:
            explanation["check_on_viewing"].append("Проверить шумоизоляцию и безопасность окон")

        if not amenities.get("parking"):
            explanation["check_on_viewing"].append("Уточнить возможность парковки во дворе")

        building_year = listing.get("building_year")
        if building_year and building_year < 2000:
            explanation["check_on_viewing"].append("Проверить состояние коммуникаций (особенно трубы)")

        return explanation


# Global instance
property_scoring_service = PropertyScoringService()
