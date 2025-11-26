"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import secrets
import structlog

logger = structlog.get_logger()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_env: str = "development"
    debug: bool = False  # Secure by default - enable explicitly for development
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000
    app_base_url: str = "https://example.com"

    # Telegram Bot
    telegram_bot_token: str
    telegram_webhook_secret: Optional[str] = None
    telegram_webapp_url: str = "https://example.com"  # WebApp URL for menu button

    # Anthropic Claude API (optional - can use Yandex GPT instead)
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-2"
    anthropic_model_fast: str = "claude-instant-1.2"

    # Radicale CalDAV Server (local multi-user calendar)
    radicale_url: str = "http://radicale:5232"
    radicale_admin_user: str = ""
    radicale_admin_password: str = ""
    radicale_bot_user: str = "calendar_bot"
    radicale_bot_password: Optional[str] = None

    # OpenAI (for Whisper - optional, can use Yandex STT)
    openai_api_key: Optional[str] = None

    # Yandex GPT (for regions where Claude/OpenAI are blocked)
    yandex_gpt_api_key: Optional[str] = None
    yandex_gpt_folder_id: Optional[str] = None

    # Security
    cors_origins: str = "https://example.com,https://webapp.telegram.org"

    # Timezone
    default_timezone: str = "Europe/Moscow"

    # Rate Limiting
    max_requests_per_user_per_day: int = 20
    max_concurrent_requests: int = 100

    def __init__(self, **kwargs):
        """Initialize settings with security validation."""
        super().__init__(**kwargs)

        # Only validate in production environment
        if self.app_env == "production":
            # Validate SECRET_KEY is not default/weak
            if not self.telegram_webhook_secret or len(self.telegram_webhook_secret) < 32:
                raise ValueError(
                    "telegram_webhook_secret must be set to a secure value (minimum 32 characters). "
                    "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )

            # Validate Radicale password is set
            if not self.radicale_bot_password:
                raise ValueError(
                    "RADICALE_BOT_PASSWORD must be set in .env for security. "
                    "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(24))'"
                )
        else:
            # Development mode - warn if using weak secrets
            if self.telegram_webhook_secret and len(self.telegram_webhook_secret) < 32:
                logger.warning("weak_secret_key",
                             message="telegram_webhook_secret is too short (< 32 chars). OK for dev, but change for production!")
            if not self.radicale_bot_password:
                logger.warning("missing_radicale_password",
                             message="RADICALE_BOT_PASSWORD not set. OK for dev, but required for production!")

    # Property Bot Settings
    property_feed_url: Optional[str] = None

    # Yandex Maps & Vision APIs (optional)
    yandex_maps_api_key: Optional[str] = None
    yandex_vision_api_key: Optional[str] = None

    # Feature Flags
    enable_poi_enrichment: bool = True
    enable_route_enrichment: bool = False
    enable_vision_enrichment: bool = False
    enable_price_context: bool = True
    enable_developer_reputation: bool = True

    # Cache Settings
    poi_cache_ttl_days: int = 7
    route_cache_ttl_days: int = 30
    price_cache_ttl_hours: int = 24

    # Search Settings
    default_search_limit: int = 100
    max_search_limit: int = 500

    # Rate Limiting for Property Search
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 10


# Global settings instance
settings = Settings()
