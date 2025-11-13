"""STT (Speech to Text) service fallback."""

import structlog

logger = structlog.get_logger()


class DummySTTService:
    """Dummy STT service for fallback when real STT is not available."""

    async def transcribe_voice(self, voice_data: bytes) -> str:
        """Mock transcription service."""
        logger.warning("dummy_stt_used", message="Real STT service not configured")
        return "Функция голосового ввода временно недоступна"


# Create a dummy instance
stt_service = DummySTTService()
