"""Speech-to-Text service using Yandex SpeechKit."""

from typing import Optional
import tempfile
from pathlib import Path
import aiohttp
import structlog
import subprocess
import os
import asyncio
import json

from app.config import settings

logger = structlog.get_logger()


class STTServiceYandex:
    """
    Speech-to-Text service using Yandex SpeechKit.

    This is a drop-in replacement for OpenAI Whisper STT service.
    Works from Russia without restrictions.

    Supports both short (<30s) and long (any duration) audio:
    - Short audio: uses synchronous STT API (fast, ~1 sec)
    - Long audio: converts to WAV and uses asynchronous recognition (slower, ~30 sec)
    """

    def __init__(self):
        """Initialize STT service with Yandex SpeechKit."""
        self.api_key = settings.yandex_gpt_api_key
        self.folder_id = settings.yandex_gpt_folder_id
        # Yandex SpeechKit STT API endpoints
        self.short_api_url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
        self.long_api_url = "https://transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize"
        # Maximum duration for short recognition (seconds)
        self.max_short_duration = 30

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        language: str = "ru"
    ) -> Optional[str]:
        """
        Transcribe audio to text using Yandex SpeechKit.

        Automatically chooses between short (fast) and long (slower) recognition
        based on audio duration.

        Args:
            audio_bytes: Audio file bytes (OGG, MP3, WAV, etc.)
            language: Language code (ru-RU, en-US, etc.)

        Returns:
            Transcribed text or None if failed

        Example:
            >>> text = await transcribe_audio(audio_data, language="ru")
            >>> print(text)  # "Запланируй встречу на завтра"
        """
        try:
            # Check audio duration
            duration = await self._get_audio_duration(audio_bytes)

            # Convert language code to Yandex format
            lang_map = {
                "ru": "ru-RU",
                "en": "en-US",
                "uk": "uk-UA",
                "kk": "kk-KZ",
                "uz": "uz-UZ"
            }
            yandex_lang = lang_map.get(language, "ru-RU")

            # Choose API based on duration
            if duration and duration > self.max_short_duration:
                logger.info(
                    "using_long_audio_recognition",
                    duration=duration,
                    method="chunked_transcription"
                )
                # Use chunked transcription for long audio (splits into 25s chunks)
                return await self._transcribe_long_audio(audio_bytes, yandex_lang)
            else:
                logger.info(
                    "using_short_audio_recognition",
                    duration=duration,
                    method="sync_oggopus"
                )
                # Use short audio recognition (fast, <30s only)
                return await self._transcribe_short_audio(audio_bytes, yandex_lang)

        except Exception as e:
            logger.error("transcription_error_yandex", error=str(e), exc_info=True)
            return None

    async def _transcribe_short_audio(
        self,
        audio_bytes: bytes,
        language: str
    ) -> Optional[str]:
        """
        Transcribe short audio (<30s) using synchronous API.
        Fast but limited to 30 seconds.
        """
        try:
            headers = {
                "Authorization": f"Api-Key {self.api_key}",
            }

            params = {
                "lang": language,
                "folderId": self.folder_id,
                "format": "oggopus",
                "sampleRateHertz": "48000"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.short_api_url,
                    headers=headers,
                    params=params,
                    data=audio_bytes,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        logger.error(
                            "yandex_stt_short_api_error",
                            status_code=response.status,
                            response=response_text
                        )
                        return None

                    result = await response.json()
                    text = result.get("result", "")

                    if not text:
                        logger.warning("yandex_stt_empty_result", result=result)
                        return None

                    logger.info(
                        "audio_transcribed_short",
                        text_length=len(text),
                        language=language
                    )

                    return text.strip()

        except Exception as e:
            logger.error("short_transcription_error", error=str(e))
            return None

    async def _transcribe_long_audio(
        self,
        audio_bytes: bytes,
        language: str
    ) -> Optional[str]:
        """
        Transcribe long audio (>30s) by splitting into chunks.
        Each chunk is transcribed separately and results are combined.
        """
        try:
            # Split audio into 25-second chunks with overlap
            chunks = await self._split_audio_into_chunks(audio_bytes, chunk_duration=25)

            if not chunks:
                logger.error("audio_splitting_failed")
                return None

            logger.info("audio_split_into_chunks", chunk_count=len(chunks))

            # Transcribe each chunk
            transcriptions = []
            for i, chunk_bytes in enumerate(chunks):
                logger.info("transcribing_chunk", chunk_num=i+1, total_chunks=len(chunks))

                # Use short audio API for each chunk (all chunks are <30s)
                text = await self._transcribe_short_audio(chunk_bytes, language)

                if text:
                    transcriptions.append(text)
                else:
                    logger.warning("chunk_transcription_failed", chunk_num=i+1)

            if not transcriptions:
                logger.error("all_chunks_failed")
                return None

            # Combine transcriptions
            full_text = " ".join(transcriptions)

            logger.info(
                "audio_transcribed_long",
                text_length=len(full_text),
                chunks_used=len(transcriptions),
                language=language
            )

            return full_text.strip()

        except Exception as e:
            logger.error("long_transcription_error", error=str(e))
            return None

    async def _split_audio_into_chunks(
        self,
        audio_bytes: bytes,
        chunk_duration: int = 25
    ) -> list[bytes]:
        """
        Split audio into chunks of specified duration (in seconds).
        Returns list of audio chunks in OGG format.
        """
        try:
            # Save input audio to temp file
            with tempfile.NamedTemporaryFile(suffix=".oga", delete=False) as input_file:
                input_file.write(audio_bytes)
                input_path = input_file.name

            chunks = []
            chunk_num = 0

            try:
                # Get total duration first
                duration = await self._get_audio_duration(audio_bytes)
                if not duration:
                    return []

                # Split audio into chunks
                current_time = 0
                while current_time < duration:
                    output_path = f"{input_path}.chunk{chunk_num}.oga"

                    # Use ffmpeg to extract chunk
                    result = subprocess.run(
                        [
                            "ffmpeg",
                            "-i", input_path,
                            "-ss", str(current_time),  # Start time
                            "-t", str(chunk_duration),  # Duration
                            "-c", "copy",  # Copy codec (no re-encoding)
                            "-y",  # Overwrite output
                            output_path
                        ],
                        capture_output=True,
                        timeout=30
                    )

                    if result.returncode != 0:
                        logger.error(
                            "chunk_extraction_failed",
                            chunk_num=chunk_num,
                            stderr=result.stderr.decode()
                        )
                        break

                    # Read chunk
                    with open(output_path, "rb") as f:
                        chunk_bytes = f.read()
                        chunks.append(chunk_bytes)

                    # Clean up chunk file
                    os.unlink(output_path)

                    current_time += chunk_duration
                    chunk_num += 1

                return chunks

            finally:
                # Clean up input file
                if os.path.exists(input_path):
                    os.unlink(input_path)

        except Exception as e:
            logger.error("audio_splitting_error", error=str(e))
            return []

    async def _convert_to_wav(self, audio_bytes: bytes) -> Optional[bytes]:
        """
        Convert audio (OGG/MP3/etc) to WAV LPCM 8kHz mono for Yandex STT.
        Returns WAV bytes without header (raw PCM).
        Uses 8kHz to keep file size under 1 MB limit for Yandex API.
        """
        try:
            # Save input audio to temp file
            with tempfile.NamedTemporaryFile(suffix=".oga", delete=False) as input_file:
                input_file.write(audio_bytes)
                input_path = input_file.name

            # Create output path
            output_path = input_path.replace(".oga", ".wav")

            try:
                # Convert using ffmpeg with 8kHz to reduce file size
                result = subprocess.run(
                    [
                        "ffmpeg",
                        "-i", input_path,
                        "-acodec", "pcm_s16le",  # Linear PCM 16-bit
                        "-ar", "8000",  # 8kHz sample rate (smaller files)
                        "-ac", "1",  # Mono
                        "-f", "s16le",  # Output format: signed 16-bit little-endian
                        "-y",  # Overwrite output
                        output_path
                    ],
                    capture_output=True,
                    timeout=30
                )

                if result.returncode != 0:
                    logger.error("ffmpeg_conversion_failed", stderr=result.stderr.decode())
                    return None

                # Read converted WAV (raw PCM without header)
                with open(output_path, "rb") as f:
                    wav_bytes = f.read()

                logger.info("audio_converted_to_wav", size_bytes=len(wav_bytes))
                return wav_bytes

            finally:
                # Clean up temp files
                if os.path.exists(input_path):
                    os.unlink(input_path)
                if os.path.exists(output_path):
                    os.unlink(output_path)

        except Exception as e:
            logger.error("wav_conversion_error", error=str(e))
            return None

    async def _get_audio_duration(self, audio_bytes: bytes) -> Optional[float]:
        """
        Get audio duration using ffprobe.
        Returns duration in seconds or None if failed.
        """
        try:
            # Save audio to temp file
            with tempfile.NamedTemporaryFile(suffix=".oga", delete=False) as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = tmp_file.name

            try:
                # Use ffprobe to get duration
                result = subprocess.run(
                    [
                        "ffprobe",
                        "-v", "error",
                        "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1",
                        tmp_path
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0 and result.stdout.strip():
                    duration = float(result.stdout.strip())
                    return duration
                else:
                    logger.warning("ffprobe_failed", stderr=result.stderr)
                    return None

            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except Exception as e:
            logger.warning("audio_duration_check_failed", error=str(e))
            # Return None to proceed with transcription anyway
            return None


# Global instance
stt_service_yandex = STTServiceYandex()
