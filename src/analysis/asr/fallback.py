"""
Cloud ASR Fallback
------------------
Used when the circuit breaker opens (local model failed/low confidence).
Supports Deepgram and AssemblyAI.
Both are optional - if no API key is configured, fallback is disabled.
"""

import httpx
import base64
from typing import Optional
from dataclasses import dataclass, field

from src.core.config import settings
from src.core.logger import logger


@dataclass
class WordTimestamp:
    word: str
    start: float
    end: float
    confidence: float


@dataclass
class FallbackTranscriptResult:
    success: bool
    transcript: str = ""
    words: list = field(default_factory=list)
    language: str = "en"
    mean_confidence: float = 0.0
    provider: str = ""
    error_message: Optional[str] = None


async def transcribe_with_deepgram(audio_path: str) -> FallbackTranscriptResult:
    """
    Transcribe using Deepgram Nova-2 API.
    Provides word-level timestamps and confidence scores.
    Only called when circuit breaker is OPEN.
    """
    if not settings.deepgram_api_key:
        return FallbackTranscriptResult(
            success=False,
            error_message="Deepgram API key not configured in .env"
        )

    try:
        with open(audio_path, "rb") as f:
            audio_data = f.read()

        headers = {
            "Authorization": f"Token {settings.deepgram_api_key}",
            "Content-Type": "audio/wav",
        }

        params = {
            "model": "nova-2",
            "language": "en",
            "punctuate": "true",
            "words": "true",
            "utterances": "false",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.deepgram.com/v1/listen",
                headers=headers,
                params=params,
                content=audio_data,
            )
            response.raise_for_status()
            data = response.json()

        # Parse Deepgram response
        channel = data["results"]["channels"][0]["alternatives"][0]
        transcript = channel.get("transcript", "")
        raw_words = channel.get("words", [])

        words = [
            WordTimestamp(
                word=w["word"],
                start=w["start"],
                end=w["end"],
                confidence=w.get("confidence", 0.9),
            )
            for w in raw_words
        ]

        mean_confidence = (
            sum(w.confidence for w in words) / len(words)
            if words else 0.0
        )

        logger.info(f"Deepgram transcription: {len(words)} words, confidence: {mean_confidence:.2f}")

        return FallbackTranscriptResult(
            success=True,
            transcript=transcript,
            words=words,
            language="en",
            mean_confidence=mean_confidence,
            provider="deepgram",
        )

    except Exception as e:
        logger.error(f"Deepgram fallback failed: {e}")
        return FallbackTranscriptResult(
            success=False,
            error_message=str(e),
            provider="deepgram",
        )


async def transcribe_with_cloud(audio_path: str) -> FallbackTranscriptResult:
    """
    Main cloud fallback entry point.
    Tries Deepgram first, then AssemblyAI if Deepgram fails.
    """
    logger.warning(f"Using cloud ASR fallback for: {audio_path}")

    # Try Deepgram first
    if settings.deepgram_api_key:
        result = await transcribe_with_deepgram(audio_path)
        if result.success:
            return result
        logger.warning("Deepgram failed - no other fallback configured")

    return FallbackTranscriptResult(
        success=False,
        error_message=(
            "All cloud fallbacks failed or no API keys configured. "
            "Add DEEPGRAM_API_KEY to .env to enable cloud fallback."
        )
    )