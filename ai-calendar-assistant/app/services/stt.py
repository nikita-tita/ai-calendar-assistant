"""Speech-to-Text service using OpenAI Whisper."""

from typing import Optional
import tempfile
from pathlib import Path
import openai
import structlog

from app.config import settings

logger = structlog.get_logger()


class STTService:
    """Speech-to-Text service using OpenAI Whisper API."""

    def __init__(self):
        """Initialize STT service."""
        self.client = openai.OpenAI(api_key=settings.openai_api_key)

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        language: str = "ru"
    ) -> Optional[str]:
        """
        Transcribe audio to text.

        Args:
            audio_bytes: Audio file bytes (OGG, MP3, WAV, etc.)
            language: Language code (ru, en, etc.)

        Returns:
            Transcribed text or None if failed

        Example:
            >>> text = await transcribe_audio(audio_data, language="ru")
            >>> print(text)  # "Запланируй встречу на завтра"
        """
        try:
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name

            try:
                # Transcribe using Whisper API
                with open(temp_path, "rb") as audio_file:
                    transcript = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language=language,
                        response_format="text"
                    )

                text = transcript if isinstance(transcript, str) else transcript.text

                logger.info(
                    "audio_transcribed",
                    text_length=len(text),
                    language=language
                )

                return text.strip()

            finally:
                # Clean up temp file
                Path(temp_path).unlink(missing_ok=True)

        except Exception as e:
            logger.error("transcription_error", error=str(e), exc_info=True)
            return None


# Global instance
stt_service = STTService()
