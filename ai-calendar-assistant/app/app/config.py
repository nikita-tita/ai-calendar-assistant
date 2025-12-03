"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional
import sys


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_env: str = "production"
    debug: bool = False
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    # Telegram Bot
    telegram_bot_token: str
    telegram_webhook_secret: Optional[str] = None
    telegram_webhook_url: Optional[str] = None
    telegram_webapp_url: Optional[str] = None

    # Anthropic Claude API (optional - can use Yandex GPT instead)
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-2"
    anthropic_model_fast: str = "claude-instant-1.2"

    # Radicale CalDAV Server (local multi-user calendar)
    radicale_url: str = "http://radicale:5232"
    radicale_admin_user: str = ""
    radicale_admin_password: str = ""
    radicale_bot_user: str = "calendar_bot"
    radicale_bot_password: str  # REQUIRED: Must be set in .env

    # OpenAI (for Whisper - optional, can use Yandex STT)
    openai_api_key: Optional[str] = None

    # Yandex GPT (for regions where Claude/OpenAI are blocked)
    yandex_gpt_api_key: Optional[str] = None
    yandex_gpt_folder_id: Optional[str] = None

    # Database
    database_url: str = "sqlite:///./calendar_assistant.db"

    # Security
    secret_key: str  # REQUIRED: Must be set in .env (min 32 chars)
    jwt_secret: Optional[str] = None
    encryption_key: Optional[str] = None
    cors_origins: str = "https://этонесамыйдлинныйдомен.рф,https://webapp.telegram.org"

    # Timezone
    default_timezone: str = "Europe/Moscow"

    # Rate Limiting
    max_requests_per_user_per_day: int = 20
    max_concurrent_requests: int = 100

    # Property Bot Settings
    property_feed_url: Optional[str] = None
    db_password: Optional[str] = None
    property_database_url: Optional[str] = None

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

    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate SECRET_KEY meets minimum security requirements."""
        if not v:
            print("❌ CRITICAL: SECRET_KEY is not set in .env file!", file=sys.stderr)
            sys.exit(1)
        if len(v) < 32:
            print(f"❌ CRITICAL: SECRET_KEY must be at least 32 characters long (current: {len(v)})", file=sys.stderr)
            print("Generate a secure key with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"", file=sys.stderr)
            sys.exit(1)
        return v

    @field_validator('radicale_bot_password')
    @classmethod
    def validate_radicale_password(cls, v: str) -> str:
        """Validate RADICALE_BOT_PASSWORD is set."""
        if not v:
            print("❌ CRITICAL: RADICALE_BOT_PASSWORD is not set in .env file!", file=sys.stderr)
            print("Generate a secure password with: python -c \"import secrets; print(secrets.token_urlsafe(24))\"", file=sys.stderr)
            sys.exit(1)
        return v


# Global settings instance
settings = Settings()
