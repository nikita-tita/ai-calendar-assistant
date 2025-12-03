"""Developer reputation system for real estate companies."""

from typing import Dict, Any, List, Optional
import structlog
from datetime import datetime
from enum import Enum

logger = structlog.get_logger()


class ReputationTier(str, Enum):
    """Developer reputation tiers."""
    PREMIUM = "premium"  # Top-tier, proven track record
    RELIABLE = "reliable"  # Good reputation, consistent quality
    AVERAGE = "average"  # Standard developer
    CAUTION = "caution"  # Some concerns
    UNKNOWN = "unknown"  # No data


class DeveloperReputationService:
    """
    Manage and assess developer reputation.

    Scoring factors:
    - Completed projects count
    - On-time delivery rate
    - Quality rating (from reviews)
    - Legal issues count
    - Years in business
    - Financial stability

    Data sources:
    - Internal database
    - Public records
    - User reviews
    """

    # Built-in knowledge base of major Moscow developers
    # In production, this would be a database
    DEVELOPER_DATABASE = {
        "ПИК": {
            "full_name": "ПАО «Группа компаний ПИК»",
            "founded_year": 1994,
            "completed_projects": 250,
            "active_projects": 45,
            "on_time_delivery_pct": 85,
            "quality_score": 7.5,  # Out of 10
            "legal_issues_count": 3,
            "financial_rating": "A",  # A, B, C, D
            "tier": ReputationTier.RELIABLE,
            "website": "https://www.pik.ru",
            "description": "Крупнейший застройщик России, специализируется на массовом строительстве"
        },
        "ЛСР": {
            "full_name": "Группа ЛСР",
            "founded_year": 1993,
            "completed_projects": 180,
            "active_projects": 25,
            "on_time_delivery_pct": 92,
            "quality_score": 8.5,
            "legal_issues_count": 1,
            "financial_rating": "A",
            "tier": ReputationTier.PREMIUM,
            "website": "https://www.lsrgroup.ru",
            "description": "Премиальный застройщик, высокое качество строительства"
        },
        "Самолет": {
            "full_name": "ГК «Самолет»",
            "founded_year": 2012,
            "completed_projects": 80,
            "active_projects": 30,
            "on_time_delivery_pct": 88,
            "quality_score": 8.0,
            "legal_issues_count": 2,
            "financial_rating": "A",
            "tier": ReputationTier.RELIABLE,
            "website": "https://samolet.ru",
            "description": "Быстрорастущий застройщик, фокус на комфорт-классе"
        },
        "МИЦ": {
            "full_name": "ГК «МИЦ»",
            "founded_year": 1994,
            "completed_projects": 160,
            "active_projects": 20,
            "on_time_delivery_pct": 90,
            "quality_score": 8.2,
            "legal_issues_count": 1,
            "financial_rating": "A",
            "tier": ReputationTier.RELIABLE,
            "website": "https://gkmic.ru",
            "description": "Надежный застройщик с многолетним опытом"
        },
        "Эталон": {
            "full_name": "ГК «Эталон»",
            "founded_year": 1987,
            "completed_projects": 200,
            "active_projects": 35,
            "on_time_delivery_pct": 87,
            "quality_score": 8.0,
            "legal_issues_count": 2,
            "financial_rating": "A",
            "tier": ReputationTier.RELIABLE,
            "website": "https://www.etalongroup.com",
            "description": "Один из старейших застройщиков, разнообразный портфель"
        },
        "А101": {
            "full_name": "Группа А101",
            "founded_year": 2003,
            "completed_projects": 120,
            "active_projects": 40,
            "on_time_delivery_pct": 83,
            "quality_score": 7.8,
            "legal_issues_count": 4,
            "financial_rating": "B",
            "tier": ReputationTier.AVERAGE,
            "website": "https://a101.ru",
            "description": "Крупный застройщик, масштабные проекты"
        }
    }

    def __init__(self):
        """Initialize developer reputation service."""
        logger.info("developer_reputation_service_initialized",
                   developers_in_db=len(self.DEVELOPER_DATABASE))

    async def get_developer_reputation(
        self,
        developer_name: str
    ) -> Dict[str, Any]:
        """
        Get comprehensive developer reputation data.

        Args:
            developer_name: Developer name (can be partial)

        Returns:
            Reputation data dictionary:
            {
                "developer_name": str,
                "full_name": str,
                "tier": str,  # premium/reliable/average/caution/unknown
                "reputation_score": float,  # 0-100
                "founded_year": int,
                "years_in_business": int,
                "completed_projects": int,
                "active_projects": int,
                "on_time_delivery_pct": float,
                "quality_score": float,  # 0-10
                "legal_issues_count": int,
                "financial_rating": str,  # A/B/C/D
                "strengths": List[str],
                "concerns": List[str],
                "recommendation": str,
                "website": str,
                "description": str
            }
        """
        logger.info("getting_developer_reputation",
                   developer_name=developer_name)

        # Find developer in database (fuzzy match)
        dev_data = self._find_developer(developer_name)

        if not dev_data:
            # Unknown developer
            return self._unknown_developer_data(developer_name)

        # Calculate reputation score
        reputation_score = self._calculate_reputation_score(dev_data)

        # Identify strengths and concerns
        strengths, concerns = self._analyze_developer(dev_data)

        # Generate recommendation
        recommendation = self._generate_recommendation(dev_data, reputation_score)

        # Calculate years in business
        years_in_business = datetime.now().year - dev_data["founded_year"]

        reputation_data = {
            "developer_name": developer_name,
            "full_name": dev_data["full_name"],
            "tier": dev_data["tier"].value,
            "reputation_score": reputation_score,
            "founded_year": dev_data["founded_year"],
            "years_in_business": years_in_business,
            "completed_projects": dev_data["completed_projects"],
            "active_projects": dev_data["active_projects"],
            "on_time_delivery_pct": dev_data["on_time_delivery_pct"],
            "quality_score": dev_data["quality_score"],
            "legal_issues_count": dev_data["legal_issues_count"],
            "financial_rating": dev_data["financial_rating"],
            "strengths": strengths,
            "concerns": concerns,
            "recommendation": recommendation,
            "website": dev_data["website"],
            "description": dev_data["description"]
        }

        logger.info("developer_reputation_retrieved",
                   developer=developer_name,
                   tier=dev_data["tier"].value,
                   score=reputation_score)

        return reputation_data

    def _find_developer(self, name: str) -> Optional[Dict[str, Any]]:
        """Find developer in database by name (fuzzy match)."""
        name_lower = name.lower().strip()

        # Exact match first
        for dev_name, dev_data in self.DEVELOPER_DATABASE.items():
            if dev_name.lower() == name_lower:
                return dev_data

        # Partial match
        for dev_name, dev_data in self.DEVELOPER_DATABASE.items():
            if name_lower in dev_name.lower() or dev_name.lower() in name_lower:
                return dev_data

        # Check full name
        for dev_name, dev_data in self.DEVELOPER_DATABASE.items():
            if name_lower in dev_data["full_name"].lower():
                return dev_data

        return None

    def _calculate_reputation_score(self, dev_data: Dict[str, Any]) -> float:
        """
        Calculate overall reputation score (0-100).

        Components:
        - On-time delivery: 30%
        - Quality score: 25%
        - Experience (years): 15%
        - Completed projects: 15%
        - Legal issues penalty: -10%
        - Financial rating: 15%
        """
        score = 0.0

        # On-time delivery (30 points max)
        on_time_pct = dev_data["on_time_delivery_pct"]
        score += (on_time_pct / 100) * 30

        # Quality score (25 points max)
        quality = dev_data["quality_score"]  # 0-10
        score += (quality / 10) * 25

        # Experience - years in business (15 points max)
        years = datetime.now().year - dev_data["founded_year"]
        experience_score = min(years / 30 * 15, 15)  # Max at 30 years
        score += experience_score

        # Completed projects (15 points max)
        projects = dev_data["completed_projects"]
        projects_score = min(projects / 200 * 15, 15)  # Max at 200 projects
        score += projects_score

        # Legal issues penalty
        legal_issues = dev_data["legal_issues_count"]
        penalty = min(legal_issues * 3, 10)  # -3 points per issue, max -10
        score -= penalty

        # Financial rating (15 points max)
        rating_scores = {"A": 15, "B": 10, "C": 5, "D": 0}
        score += rating_scores.get(dev_data["financial_rating"], 0)

        return round(min(max(score, 0), 100), 1)

    def _analyze_developer(
        self,
        dev_data: Dict[str, Any]
    ) -> tuple[List[str], List[str]]:
        """
        Identify developer strengths and concerns.

        Args:
            dev_data: Developer data

        Returns:
            Tuple of (strengths, concerns)
        """
        strengths = []
        concerns = []

        # On-time delivery
        if dev_data["on_time_delivery_pct"] >= 90:
            strengths.append("Стабильно сдают объекты в срок (90%+)")
        elif dev_data["on_time_delivery_pct"] < 80:
            concerns.append(f"Задержки сдачи объектов ({dev_data['on_time_delivery_pct']}%)")

        # Quality
        if dev_data["quality_score"] >= 8.5:
            strengths.append("Высокое качество строительства (8.5+/10)")
        elif dev_data["quality_score"] < 7.0:
            concerns.append(f"Средняя оценка качества ({dev_data['quality_score']}/10)")

        # Experience
        years = datetime.now().year - dev_data["founded_year"]
        if years >= 25:
            strengths.append(f"Многолетний опыт ({years} лет на рынке)")

        # Portfolio
        if dev_data["completed_projects"] >= 150:
            strengths.append(f"Большое портфолио ({dev_data['completed_projects']} проектов)")

        # Financial stability
        if dev_data["financial_rating"] == "A":
            strengths.append("Высокая финансовая стабильность (рейтинг A)")
        elif dev_data["financial_rating"] in ["C", "D"]:
            concerns.append(f"Средняя финансовая стабильность (рейтинг {dev_data['financial_rating']})")

        # Legal issues
        if dev_data["legal_issues_count"] == 0:
            strengths.append("Нет юридических проблем")
        elif dev_data["legal_issues_count"] >= 3:
            concerns.append(f"Есть юридические вопросы ({dev_data['legal_issues_count']} случаев)")

        return strengths, concerns

    def _generate_recommendation(
        self,
        dev_data: Dict[str, Any],
        reputation_score: float
    ) -> str:
        """Generate recommendation text based on tier and score."""
        tier = dev_data["tier"]

        recommendations = {
            ReputationTier.PREMIUM: "✅ Премиальный застройщик. Рекомендуем - высочайшее качество и надежность.",
            ReputationTier.RELIABLE: "✅ Надежный застройщик. Рекомендуем - стабильное качество и своевременная сдача.",
            ReputationTier.AVERAGE: "⚖️ Стандартный застройщик. Допустимо, но изучите детали конкретного проекта.",
            ReputationTier.CAUTION: "⚠️ Требует осторожности. Внимательно изучите условия и отзывы.",
            ReputationTier.UNKNOWN: "❓ Недостаточно данных. Рекомендуем дополнительную проверку."
        }

        recommendation = recommendations.get(tier, "")

        # Add score context
        if reputation_score >= 80:
            recommendation += f" Репутация: {reputation_score}/100 (отлично)."
        elif reputation_score >= 60:
            recommendation += f" Репутация: {reputation_score}/100 (хорошо)."
        elif reputation_score >= 40:
            recommendation += f" Репутация: {reputation_score}/100 (удовлетворительно)."
        else:
            recommendation += f" Репутация: {reputation_score}/100 (ниже среднего)."

        return recommendation

    def _unknown_developer_data(self, developer_name: str) -> Dict[str, Any]:
        """Return data structure for unknown developer."""
        return {
            "developer_name": developer_name,
            "full_name": developer_name,
            "tier": ReputationTier.UNKNOWN.value,
            "reputation_score": None,
            "founded_year": None,
            "years_in_business": None,
            "completed_projects": None,
            "active_projects": None,
            "on_time_delivery_pct": None,
            "quality_score": None,
            "legal_issues_count": None,
            "financial_rating": None,
            "strengths": [],
            "concerns": ["Нет данных о застройщике в базе"],
            "recommendation": "❓ Неизвестный застройщик. Рекомендуем тщательную проверку перед покупкой.",
            "website": None,
            "description": "Информация о застройщике отсутствует в базе данных"
        }

    def get_reputation_summary(
        self,
        reputation_data: Dict[str, Any]
    ) -> str:
        """
        Generate human-readable reputation summary.

        Args:
            reputation_data: Reputation data from get_developer_reputation()

        Returns:
            Human-readable summary in Russian
        """
        parts = []

        # Tier badge
        tier_badges = {
            "premium": "⭐ Премиум",
            "reliable": "✅ Надежный",
            "average": "⚖️ Стандартный",
            "caution": "⚠️ Осторожно",
            "unknown": "❓ Неизвестен"
        }
        tier = reputation_data.get("tier")
        parts.append(tier_badges.get(tier, ""))

        # Score
        score = reputation_data.get("reputation_score")
        if score:
            parts.append(f"Репутация: {score}/100")

        # Key strength
        strengths = reputation_data.get("strengths", [])
        if strengths:
            parts.append(strengths[0])  # Top strength

        # Key concern
        concerns = reputation_data.get("concerns", [])
        if concerns:
            parts.append(f"⚠️ {concerns[0]}")  # Top concern

        return "\n".join(parts) if parts else "Данные о застройщике отсутствуют"

    def compare_developers(
        self,
        developer_names: List[str]
    ) -> Dict[str, Any]:
        """
        Compare multiple developers side-by-side.

        Args:
            developer_names: List of developer names

        Returns:
            Comparison data with rankings
        """
        comparisons = []

        for name in developer_names:
            rep_data = self.get_developer_reputation(name)
            comparisons.append(rep_data)

        # Sort by reputation score
        comparisons.sort(
            key=lambda x: x.get("reputation_score") or 0,
            reverse=True
        )

        return {
            "developers": comparisons,
            "best": comparisons[0] if comparisons else None,
            "total_compared": len(comparisons)
        }


# Global instance
developer_reputation_service = DeveloperReputationService()
