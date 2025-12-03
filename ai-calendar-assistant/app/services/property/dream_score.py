"""Dream Score calculation for property listings."""

from typing import Dict, Any, Optional
import structlog

from app.schemas.property import PropertyListingResponse, PropertyClientResponse

logger = structlog.get_logger()


class DreamScoreCalculator:
    """
    Calculate Dream Score (0-100) for property listings based on client preferences.

    Components (each 0-100):
    1. price_match (20%): How well price fits budget
    2. location (15%): Metro distance + district match
    3. space (10%): Rooms and area match
    4. floor (5%): Floor preferences
    5. layout (15%): Balcony, bathroom, ceiling height
    6. building_quality (15%): Building type, renovation, year
    7. financial (10%): Mortgage, payment methods, haggle
    8. infrastructure (5%): School, kindergarten, park
    9. amenities (5%): Elevator, parking, pets

    Total: 100%
    """

    # Component weights
    WEIGHTS = {
        "price_match": 0.20,
        "location": 0.15,
        "space": 0.10,
        "floor": 0.05,
        "layout": 0.15,
        "building_quality": 0.15,
        "financial": 0.10,
        "infrastructure": 0.05,
        "amenities": 0.05
    }

    @staticmethod
    def calculate(
        listing: PropertyListingResponse,
        client: PropertyClientResponse
    ) -> Dict[str, Any]:
        """
        Calculate Dream Score and component breakdown.

        Args:
            listing: Property listing
            client: Client preferences

        Returns:
            Dictionary with:
            - dream_score: float (0-100)
            - components: Dict[str, float] - each component score
            - explanation: str - human-readable explanation
        """
        components = {}

        # 1. Price Match (20%)
        components["price_match"] = DreamScoreCalculator._score_price(listing, client)

        # 2. Location (15%)
        components["location"] = DreamScoreCalculator._score_location(listing, client)

        # 3. Space (10%)
        components["space"] = DreamScoreCalculator._score_space(listing, client)

        # 4. Floor (5%)
        components["floor"] = DreamScoreCalculator._score_floor(listing, client)

        # 5. Layout (15%)
        components["layout"] = DreamScoreCalculator._score_layout(listing, client)

        # 6. Building Quality (15%)
        components["building_quality"] = DreamScoreCalculator._score_building_quality(listing, client)

        # 7. Financial (10%)
        components["financial"] = DreamScoreCalculator._score_financial(listing, client)

        # 8. Infrastructure (5%)
        components["infrastructure"] = DreamScoreCalculator._score_infrastructure(listing, client)

        # 9. Amenities (5%)
        components["amenities"] = DreamScoreCalculator._score_amenities(listing, client)

        # Calculate weighted total
        dream_score = sum(
            components[key] * DreamScoreCalculator.WEIGHTS[key]
            for key in components.keys()
        )

        logger.info("dream_score_calculated",
                   listing_id=listing.id,
                   score=round(dream_score, 1),
                   components={k: round(v, 1) for k, v in components.items()})

        return {
            "dream_score": round(dream_score, 1),
            "components": {k: round(v, 1) for k, v in components.items()},
            "explanation": DreamScoreCalculator._generate_explanation(dream_score, components, listing, client)
        }

    @staticmethod
    def _score_price(listing: PropertyListingResponse, client: PropertyClientResponse) -> float:
        """Score price match (0-100)."""
        if not listing.price:
            return 50.0

        price = listing.price
        budget_min = client.budget_min or 0
        budget_max = client.budget_max or float('inf')

        # Perfect match: within budget
        if budget_min <= price <= budget_max:
            # Even better: in lower 50% of budget (value for money)
            if budget_min > 0:
                budget_range = budget_max - budget_min
                price_position = (price - budget_min) / budget_range if budget_range > 0 else 0.5

                # Lower price within budget = higher score
                # 100 at budget_min, 80 at budget_max
                return 100.0 - (price_position * 20.0)
            else:
                # If no min budget, price at max gets 80
                return 80.0 if price == budget_max else 90.0

        # Over budget: penalty
        elif price > budget_max:
            overshoot = price - budget_max
            overshoot_pct = overshoot / budget_max if budget_max > 0 else 1.0

            # -10 points per 10% over budget
            penalty = min(overshoot_pct * 100, 80)  # Max penalty 80 points
            return max(20.0 - penalty, 0.0)

        # Under minimum budget (if specified)
        elif price < budget_min and budget_min > 0:
            # Slightly suspicious but not terrible
            return 60.0

        return 50.0

    @staticmethod
    def _score_location(listing: PropertyListingResponse, client: PropertyClientResponse) -> float:
        """Score location match (0-100)."""
        score = 0.0
        points = 0

        # Metro distance (60 points max)
        if listing.metro_distance_minutes is not None:
            max_distance = client.max_metro_distance_minutes or 15
            if listing.metro_distance_minutes <= max_distance:
                # Perfect: <=5 min = 60, scales down to 30 at max_distance
                ratio = listing.metro_distance_minutes / max_distance
                score += 60.0 - (ratio * 30.0)
                points += 60
            else:
                # Over max distance: penalty
                excess = listing.metro_distance_minutes - max_distance
                penalty = min(excess * 2, 50)  # -2 points per minute over
                score += max(10.0 - penalty, 0)
                points += 60
        else:
            # No metro data: neutral
            score += 30.0
            points += 60

        # District match (40 points max)
        if client.districts and listing.district:
            if listing.district in client.districts:
                score += 40.0
            else:
                score += 10.0  # Wrong district but specified
            points += 40
        elif client.metro_stations and listing.metro_station:
            if listing.metro_station in client.metro_stations:
                score += 40.0
            else:
                score += 10.0
            points += 40
        else:
            # No location preferences: neutral
            score += 20.0
            points += 40

        return (score / points * 100) if points > 0 else 50.0

    @staticmethod
    def _score_space(listing: PropertyListingResponse, client: PropertyClientResponse) -> float:
        """Score space/rooms match (0-100)."""
        score = 0.0
        points = 0

        # Rooms (60 points)
        if listing.rooms is not None:
            rooms_min = client.rooms_min or 0
            rooms_max = client.rooms_max or 10
            if rooms_min <= listing.rooms <= rooms_max:
                score += 60.0
            else:
                # Penalty for mismatch
                diff = min(abs(listing.rooms - rooms_min), abs(listing.rooms - rooms_max))
                penalty = diff * 15  # -15 per room off
                score += max(60.0 - penalty, 0)
            points += 60
        else:
            score += 30.0
            points += 60

        # Area (40 points)
        if listing.area_total is not None:
            area_min = client.area_min or 0
            area_max = client.area_max or 1000
            if area_min <= listing.area_total <= area_max:
                score += 40.0
            else:
                # Small penalty for area mismatch
                if listing.area_total < area_min:
                    diff_pct = (area_min - listing.area_total) / area_min
                else:
                    diff_pct = (listing.area_total - area_max) / area_max
                penalty = min(diff_pct * 30, 35)
                score += max(40.0 - penalty, 5)
            points += 40
        else:
            score += 20.0
            points += 40

        return (score / points * 100) if points > 0 else 50.0

    @staticmethod
    def _score_floor(listing: PropertyListingResponse, client: PropertyClientResponse) -> float:
        """Score floor preferences (0-100)."""
        if listing.floor is None:
            return 50.0

        floor = listing.floor
        total_floors = listing.total_floors or 100

        # Check hard constraints
        if client.not_first_floor and floor == 1:
            return 0.0  # Deal breaker

        if client.not_last_floor and floor == total_floors:
            return 0.0  # Deal breaker

        # Check range preferences
        floor_min = client.floor_min or 1
        floor_max = client.floor_max or total_floors

        if floor_min <= floor <= floor_max:
            # Within range: 100 points
            # Bonus for middle floors (prefer 3-7 range for most people)
            if 3 <= floor <= 7:
                return 100.0
            else:
                return 85.0
        else:
            # Outside range: penalty
            diff = min(abs(floor - floor_min), abs(floor - floor_max))
            penalty = diff * 10  # -10 per floor
            return max(50.0 - penalty, 10.0)

    @staticmethod
    def _score_layout(listing: PropertyListingResponse, client: PropertyClientResponse) -> float:
        """Score layout preferences (0-100) - NEW ENHANCED."""
        score = 0.0
        points = 0

        # Balcony (30 points)
        if client.balcony_required:
            if listing.balcony_type:
                score += 30.0
                # Bonus if specific type matches
                if client.preferred_balcony_types and listing.balcony_type in client.preferred_balcony_types:
                    score += 5.0
                    points += 5
            else:
                score += 0.0  # Required but missing
            points += 30
        elif listing.balcony_type:
            # Not required but has it: small bonus
            score += 15.0
            points += 30
        else:
            # Not required, doesn't have: neutral
            score += 10.0
            points += 30

        # Bathroom type (25 points)
        if client.bathroom_type_preference and listing.bathroom_type:
            if listing.bathroom_type == client.bathroom_type_preference:
                score += 25.0
            else:
                score += 5.0  # Wrong type
            points += 25
        else:
            score += 12.0  # Neutral
            points += 25

        # Bathroom count (20 points)
        if client.min_bathroom_count and listing.bathroom_count:
            if listing.bathroom_count >= client.min_bathroom_count:
                score += 20.0
            else:
                diff = client.min_bathroom_count - listing.bathroom_count
                penalty = diff * 8
                score += max(20.0 - penalty, 0)
            points += 20
        else:
            score += 10.0
            points += 20

        # Ceiling height (15 points)
        if client.min_ceiling_height and listing.ceiling_height:
            if listing.ceiling_height >= client.min_ceiling_height:
                score += 15.0
                # Bonus for extra height
                if listing.ceiling_height >= client.min_ceiling_height + 0.3:
                    score += 5.0
                    points += 5
            else:
                diff = client.min_ceiling_height - listing.ceiling_height
                penalty = diff * 20  # -20 per 10cm shortage
                score += max(15.0 - penalty, 0)
            points += 15
        else:
            score += 7.0
            points += 15

        # Kitchen area (10 points)
        if client.kitchen_area_min and listing.kitchen_area:
            if listing.kitchen_area >= client.kitchen_area_min:
                score += 10.0
            else:
                diff_pct = (client.kitchen_area_min - listing.kitchen_area) / client.kitchen_area_min
                penalty = diff_pct * 8
                score += max(10.0 - penalty, 2)
            points += 10
        else:
            score += 5.0
            points += 10

        return (score / points * 100) if points > 0 else 50.0

    @staticmethod
    def _score_building_quality(listing: PropertyListingResponse, client: PropertyClientResponse) -> float:
        """Score building quality (0-100) - NEW ENHANCED."""
        score = 0.0
        points = 0

        # Building type (40 points)
        if client.preferred_building_types and listing.building_type:
            if listing.building_type in client.preferred_building_types:
                score += 40.0
            elif client.exclude_building_types and listing.building_type in client.exclude_building_types:
                score += 0.0  # Explicitly excluded
            else:
                score += 15.0  # Not preferred but not excluded
            points += 40
        elif client.exclude_building_types and listing.building_type:
            if listing.building_type in client.exclude_building_types:
                score += 0.0
            else:
                score += 30.0
            points += 40
        else:
            # No preference: rate by inherent quality
            # кирпич > монолит > кирпично-монолитный > панельный
            quality_scores = {
                "кирпичный": 35.0,
                "монолитный": 32.0,
                "кирпично-монолитный": 28.0,
                "панельный": 20.0
            }
            score += quality_scores.get(listing.building_type, 20.0)
            points += 40

        # Renovation (35 points)
        if client.preferred_renovations and listing.renovation:
            if listing.renovation in client.preferred_renovations:
                score += 35.0
            elif client.exclude_renovations and listing.renovation in client.exclude_renovations:
                score += 0.0
            else:
                score += 12.0
            points += 35
        elif client.exclude_renovations and listing.renovation:
            if listing.renovation in client.exclude_renovations:
                score += 0.0
            else:
                score += 25.0
            points += 35
        else:
            # No preference: rate by inherent quality
            renovation_scores = {
                "под ключ": 30.0,
                "чистовая": 28.0,
                "предчистовая": 20.0,
                "без отделки": 10.0
            }
            score += renovation_scores.get(listing.renovation, 15.0)
            points += 35

        # Building year/state (25 points)
        if listing.building_year:
            # Newer is better
            if listing.building_year >= 2024:
                score += 25.0
            elif listing.building_year >= 2020:
                score += 20.0
            elif listing.building_year >= 2015:
                score += 12.0
            else:
                score += 5.0
            points += 25
        elif listing.building_state:
            # "hand-over" better than "in-progress"
            if listing.building_state == "hand-over":
                score += 20.0
            else:
                score += 10.0
            points += 25
        else:
            score += 10.0
            points += 25

        return (score / points * 100) if points > 0 else 50.0

    @staticmethod
    def _score_financial(listing: PropertyListingResponse, client: PropertyClientResponse) -> float:
        """Score financial conditions (0-100) - NEW ENHANCED."""
        score = 0.0
        points = 0

        # Mortgage availability (50 points)
        if client.mortgage_required:
            if listing.mortgage_available:
                score += 50.0
            else:
                score += 0.0  # Deal breaker
            points += 50
        else:
            # Not required: neutral
            score += 25.0
            points += 50

        # Payment methods (30 points)
        if client.preferred_payment_methods and listing.payment_methods:
            # Check if any preferred method is available
            matching = set(client.preferred_payment_methods) & set(listing.payment_methods)
            if matching:
                # Score by number of matches
                match_ratio = len(matching) / len(client.preferred_payment_methods)
                score += 30.0 * match_ratio
            else:
                score += 5.0  # No matches
            points += 30
        else:
            score += 15.0
            points += 30

        # Haggle allowed (20 points)
        if listing.haggle_allowed:
            # Always a bonus
            score += 20.0
        else:
            score += 8.0
        points += 20

        return (score / points * 100) if points > 0 else 50.0

    @staticmethod
    def _score_infrastructure(listing: PropertyListingResponse, client: PropertyClientResponse) -> float:
        """Score nearby infrastructure (0-100) - NEW."""
        score = 0.0
        points = 0

        poi_data = listing.poi_data or {}

        # School nearby (40 points)
        if client.school_nearby_required:
            school_info = poi_data.get("school", {})
            if school_info.get("nearby"):
                score += 40.0
            else:
                score += 0.0  # Required but missing
            points += 40
        else:
            score += 20.0
            points += 40

        # Kindergarten nearby (35 points)
        if client.kindergarten_nearby_required:
            kindergarten_info = poi_data.get("kindergarten", {})
            if kindergarten_info.get("nearby"):
                score += 35.0
            else:
                score += 0.0
            points += 35
        else:
            score += 17.0
            points += 35

        # Park nearby (25 points)
        if client.park_nearby_required:
            park_info = poi_data.get("park", {})
            if park_info.get("nearby"):
                score += 25.0
            else:
                score += 5.0
            points += 25
        else:
            score += 12.0
            points += 25

        return (score / points * 100) if points > 0 else 50.0

    @staticmethod
    def _score_amenities(listing: PropertyListingResponse, client: PropertyClientResponse) -> float:
        """Score amenities (0-100)."""
        score = 0.0
        points = 0

        # Elevator (30 points)
        if client.requires_elevator:
            if listing.has_elevator:
                score += 30.0
            else:
                score += 0.0  # Deal breaker for high floors
            points += 30
        else:
            score += 15.0
            points += 30

        # Parking (30 points)
        if listing.has_parking:
            score += 30.0
        else:
            score += 10.0
        points += 30

        # Pets (20 points)
        if client.allows_pets and listing.allows_pets:
            score += 20.0
        elif client.allows_pets and not listing.allows_pets:
            score += 0.0
        else:
            score += 10.0
        points += 20

        # Kids (20 points)
        if client.allows_kids and listing.allows_kids:
            score += 20.0
        elif client.allows_kids and not listing.allows_kids:
            score += 5.0
        else:
            score += 10.0
        points += 20

        return (score / points * 100) if points > 0 else 50.0

    @staticmethod
    def _generate_explanation(
        dream_score: float,
        components: Dict[str, float],
        listing: PropertyListingResponse,
        client: PropertyClientResponse
    ) -> str:
        """Generate human-readable explanation of Dream Score."""
        # Find top 3 components
        sorted_components = sorted(components.items(), key=lambda x: x[1], reverse=True)
        top_3 = sorted_components[:3]

        # Component names in Russian
        component_names = {
            "price_match": "соответствие цены",
            "location": "локация",
            "space": "площадь",
            "floor": "этаж",
            "layout": "планировка",
            "building_quality": "качество дома",
            "financial": "финансовые условия",
            "infrastructure": "инфраструктура",
            "amenities": "удобства"
        }

        explanation_parts = []

        # Overall assessment
        if dream_score >= 80:
            explanation_parts.append("Отличный вариант!")
        elif dream_score >= 60:
            explanation_parts.append("Хороший вариант")
        elif dream_score >= 40:
            explanation_parts.append("Приемлемый вариант с компромиссами")
        else:
            explanation_parts.append("Вариант с существенными отличиями от требований")

        # Top strengths
        strengths = [f"{component_names.get(name, name)} ({score:.0f}%)"
                    for name, score in top_3 if score >= 70]
        if strengths:
            explanation_parts.append(f"Сильные стороны: {', '.join(strengths)}")

        # Weaknesses
        weaknesses = [f"{component_names.get(name, name)} ({score:.0f}%)"
                     for name, score in components.items() if score < 40]
        if weaknesses:
            explanation_parts.append(f"Слабые стороны: {', '.join(weaknesses)}")

        return ". ".join(explanation_parts)


# Global instance
dream_score_calculator = DreamScoreCalculator()
