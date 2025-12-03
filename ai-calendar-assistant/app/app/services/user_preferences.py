"""User preferences service for storing language and other settings."""

import json
from pathlib import Path
from typing import Dict, Optional
import structlog

from app.services.translations import Language
from app.config import settings

logger = structlog.get_logger()


class UserPreferencesService:
    """Service for managing user preferences."""

    def __init__(self, data_file: str = "/var/lib/calendar-bot/user_preferences.json"):
        """
        Initialize preferences service.

        Args:
            data_file: Path to JSON file for storing preferences
        """
        self.data_file = data_file
        self.preferences: Dict[str, dict] = {}
        self._load_data()

    def _load_data(self):
        """Load preferences from file."""
        try:
            if Path(self.data_file).exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.preferences = json.load(f)
                logger.info("user_preferences_loaded", count=len(self.preferences))
            else:
                logger.info("user_preferences_file_not_found", creating_new=True)
                self.preferences = {}
        except Exception as e:
            logger.error("failed_to_load_preferences", error=str(e))
            self.preferences = {}

    def _save_data(self):
        """Save preferences to file."""
        try:
            # Ensure directory exists
            Path(self.data_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.preferences, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("failed_to_save_preferences", error=str(e))

    def get_language(self, user_id: str) -> Language:
        """
        Get user's preferred language.

        Args:
            user_id: Telegram user ID

        Returns:
            User's language or Russian as default
        """
        prefs = self.preferences.get(user_id, {})
        lang_code = prefs.get("language", Language.RUSSIAN)
        try:
            return Language(lang_code)
        except ValueError:
            return Language.RUSSIAN

    def set_language(self, user_id: str, language: Language):
        """
        Set user's preferred language.

        Args:
            user_id: Telegram user ID
            language: Language to set
        """
        if user_id not in self.preferences:
            self.preferences[user_id] = {}

        self.preferences[user_id]["language"] = language.value
        self._save_data()

        logger.info("user_language_set", user_id=user_id, language=language)

    def has_selected_language(self, user_id: str) -> bool:
        """
        Check if user has selected a language.

        Args:
            user_id: Telegram user ID

        Returns:
            True if user has selected language, False otherwise
        """
        return user_id in self.preferences and "language" in self.preferences[user_id]

    def get_timezone(self, user_id: str) -> str:
        """
        Get user's timezone.

        Args:
            user_id: Telegram user ID

        Returns:
            Timezone string or default timezone from settings
        """
        prefs = self.preferences.get(user_id, {})
        return prefs.get("timezone", settings.default_timezone)

    def set_timezone(self, user_id: str, timezone: str):
        """
        Set user's timezone.

        Args:
            user_id: Telegram user ID
            timezone: Timezone string
        """
        if user_id not in self.preferences:
            self.preferences[user_id] = {}

        self.preferences[user_id]["timezone"] = timezone
        self._save_data()

        logger.info("user_timezone_set", user_id=user_id, timezone=timezone)

    def get_motivation_index(self, user_id: str) -> int:
        """
        Get user's current motivational message index (1-60).

        Args:
            user_id: Telegram user ID

        Returns:
            Current message index (1-60)
        """
        prefs = self.preferences.get(user_id, {})
        return prefs.get("motivation_index", 1)

    def increment_motivation_index(self, user_id: str) -> int:
        """
        Increment user's motivational message index and return new value.
        Cycles from 60 back to 1.

        Args:
            user_id: Telegram user ID

        Returns:
            New message index (1-60)
        """
        if user_id not in self.preferences:
            self.preferences[user_id] = {}

        current_index = self.get_motivation_index(user_id)
        new_index = (current_index % 60) + 1  # Cycle: 1->2->...->60->1

        self.preferences[user_id]["motivation_index"] = new_index
        self._save_data()

        logger.info("motivation_index_incremented", user_id=user_id, new_index=new_index)

        return new_index

    def get_morning_summary_enabled(self, user_id: str) -> bool:
        """Get whether morning summary is enabled."""
        prefs = self.preferences.get(user_id, {})
        return prefs.get("morning_summary_enabled", True)  # Default: enabled

    def set_morning_summary_enabled(self, user_id: str, enabled: bool):
        """Set morning summary enabled/disabled."""
        if user_id not in self.preferences:
            self.preferences[user_id] = {}
        self.preferences[user_id]["morning_summary_enabled"] = enabled
        self._save_data()
        logger.info("morning_summary_toggled", user_id=user_id, enabled=enabled)

    def get_morning_summary_time(self, user_id: str) -> str:
        """Get morning summary time (HH:MM format)."""
        prefs = self.preferences.get(user_id, {})
        return prefs.get("morning_summary_time", "07:30")

    def set_morning_summary_time(self, user_id: str, time: str):
        """Set morning summary time."""
        if user_id not in self.preferences:
            self.preferences[user_id] = {}
        self.preferences[user_id]["morning_summary_time"] = time
        self._save_data()
        logger.info("morning_summary_time_set", user_id=user_id, time=time)

    def get_evening_digest_enabled(self, user_id: str) -> bool:
        """Get whether evening digest is enabled."""
        prefs = self.preferences.get(user_id, {})
        return prefs.get("evening_digest_enabled", True)  # Default: enabled

    def set_evening_digest_enabled(self, user_id: str, enabled: bool):
        """Set evening digest enabled/disabled."""
        if user_id not in self.preferences:
            self.preferences[user_id] = {}
        self.preferences[user_id]["evening_digest_enabled"] = enabled
        self._save_data()
        logger.info("evening_digest_toggled", user_id=user_id, enabled=enabled)

    def get_evening_digest_time(self, user_id: str) -> str:
        """Get evening digest time (HH:MM format)."""
        prefs = self.preferences.get(user_id, {})
        return prefs.get("evening_digest_time", "20:00")

    def set_evening_digest_time(self, user_id: str, time: str):
        """Set evening digest time."""
        if user_id not in self.preferences:
            self.preferences[user_id] = {}
        self.preferences[user_id]["evening_digest_time"] = time
        self._save_data()
        logger.info("evening_digest_time_set", user_id=user_id, time=time)

    def get_quiet_hours(self, user_id: str) -> tuple:
        """Get quiet hours as tuple (start, end) in HH:MM format."""
        prefs = self.preferences.get(user_id, {})
        start = prefs.get("quiet_hours_start", "22:00")
        end = prefs.get("quiet_hours_end", "08:00")
        return (start, end)

    def set_quiet_hours(self, user_id: str, start: str, end: str):
        """Set quiet hours."""
        if user_id not in self.preferences:
            self.preferences[user_id] = {}
        self.preferences[user_id]["quiet_hours_start"] = start
        self.preferences[user_id]["quiet_hours_end"] = end
        self._save_data()
        logger.info("quiet_hours_set", user_id=user_id, start=start, end=end)

    def get_all_settings(self, user_id: str) -> dict:
        """Get all settings for a user."""
        prefs = self.preferences.get(user_id, {})
        quiet_start, quiet_end = self.get_quiet_hours(user_id)

        return {
            "timezone": self.get_timezone(user_id),
            "language": self.get_language(user_id).value,
            "morning_summary_enabled": self.get_morning_summary_enabled(user_id),
            "morning_summary_time": self.get_morning_summary_time(user_id),
            "evening_digest_enabled": self.get_evening_digest_enabled(user_id),
            "evening_digest_time": self.get_evening_digest_time(user_id),
            "quiet_hours_start": quiet_start,
            "quiet_hours_end": quiet_end
        }

    def get_advertising_consent(self, user_id: str) -> bool:
        """Get whether user gave advertising consent."""
        prefs = self.preferences.get(user_id, {})
        return prefs.get("advertising_consent", False)

    def set_advertising_consent(self, user_id: str, consent: bool):
        """Set advertising consent."""
        if user_id not in self.preferences:
            self.preferences[user_id] = {}
        self.preferences[user_id]["advertising_consent"] = consent
        self._save_data()
        logger.info("advertising_consent_set", user_id=user_id, consent=consent)

    def get_privacy_consent(self, user_id: str) -> bool:
        """Get whether user gave privacy consent."""
        prefs = self.preferences.get(user_id, {})
        return prefs.get("privacy_consent", False)

    def set_privacy_consent(self, user_id: str, consent: bool):
        """Set privacy consent."""
        if user_id not in self.preferences:
            self.preferences[user_id] = {}
        self.preferences[user_id]["privacy_consent"] = consent
        self._save_data()
        logger.info("privacy_consent_set", user_id=user_id, consent=consent)


# Global instance
user_preferences = UserPreferencesService()
