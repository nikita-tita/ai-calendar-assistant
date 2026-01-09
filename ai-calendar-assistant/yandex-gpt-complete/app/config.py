"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


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
    debug: bool = True
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    # Telegram Bot
    telegram_bot_token: str
    telegram_webhook_secret: Optional[str] = None
    telegram_webhook_url: Optional[str] = None

    # Anthropic Claude API
    anthropic_api_key: str
    anthropic_model: str = "claude-2"
    anthropic_model_fast: str = "claude-instant-1.2"

    # Radicale CalDAV Server (local multi-user calendar)
    radicale_url: str = "http://radicale:5232"
    radicale_admin_user: str = ""
    radicale_admin_password: str = ""

    # OpenAI (for Whisper)
    openai_api_key: str

    # Yandex GPT (for regions where Claude/OpenAI are blocked)
    yandex_gpt_api_key: Optional[str] = None
    yandex_gpt_folder_id: Optional[str] = None

    # Database
    database_url: str = "sqlite:///./calendar_assistant.db"

    # Security
    secret_key: Optional[str] = "default-secret-key-change-in-production"

    # Timezone
    default_timezone: str = "Europe/Moscow"

    # Rate Limiting
    max_requests_per_user_per_day: int = 20
    max_concurrent_requests: int = 100


# Global settings instance
settings = Settings()
