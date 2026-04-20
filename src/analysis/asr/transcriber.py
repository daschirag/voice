"""
ASR Transcriber
---------------
Primary transcription engine using faster-whisper.
Uses GPU (float16) for 5x faster inference than CPU.

Output per word:
  - text: the word string
  - start: timestamp in seconds
  - end: timestamp in seconds
  - confidence: probability 0.0-1.0

The circuit breaker monitors confidence and failure rate,
routing to cloud API if local model underperforms.
"""

import time
from dataclasses import dataclass, field
from typing import List, Optional

from faster_whisper import WhisperModel

from src.core.config import settings
from src.core.logger import logger
from src.analysis.asr.circuit_breaker import get_circuit_breaker


# ─────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────

@dataclass
class WordToken:
    """A single transcribed word with timing and confidence."""
    word: str
    start: float        # seconds from audio start
    end: float          # seconds from audio start
    confidence: float   # 0.0 to 1.0


@dataclass
class TranscriptResult:
    """Complete ASR output for one audio file."""
    success: bool
    transcript: str                          # full text
    words: List[WordToken] = field(default_factory=list)
    language: str = "en"
    language_probability: float = 0.0
    mean_confidence: float = 0.0
    low_confidence_words: List[WordToken] = field(default_factory=list)
    duration: float = 0.0
    inference_time: float = 0.0
    used_fallback: bool = False
    error_message: Optional[str] = None


# ─────────────────────────────────────────────
# Whisper Model Loader (cached singleton)
# ─────────────────────────────────────────────

_whisper_model: Optional[WhisperModel] = None


def _get_whisper_model() -> WhisperModel:
    """
    Load faster-whisper model once and cache it in memory.

    Model is loaded to GPU with float16 precision.
    First load takes ~5 seconds. Subsequent calls are instant.

    Why small.en?
    - WER ~6% on clean English speech
    - Fits in 1.5GB VRAM (leaves room for other models)
    - Processes 5-min audio in ~3-4 seconds on RTX 4050
    """
    global _whisper_model

    if _whisper_model is not None:
        return _whisper_model

    logger.info(
        f"Loading faster-whisper model: {settings.whisper_model_size} "
        f"on {settings.whisper_device} ({settings.whisper_compute_type})"
    )

    try:
        _whisper_model = WhisperModel(
            model_size_or_path=settings.whisper_model_size,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
            download_root=str(settings.models_dir / "whisper"),
            num_workers=2,
        )
        logger.success(f"faster-whisper loaded: {settings.whisper_model_size}")
        return _whisper_model

    except Exception as e:
        logger.error(f"Failed to load faster-whisper: {e}")
        raise


# ─────────────────────────────────────────────
# Core Transcription Logic
# ─────────────────────────────────────────────

def _transcribe_local(
    audio_path: str,
    job_id: str,
) -> TranscriptResult:
    """
    Transcribe using local faster-whisper model.

    Key settings explained:
      beam_size=5: balance between accuracy and speed
      word_timestamps=True: get per-word start/end times
      vad_filter=True: use built-in VAD to skip silence
        (reduces hallucinations on long audio)
      vad_parameters: silence threshold tuned to our 150ms minimum
      condition_on_previous_text=False: prevents hallucination
        on long audio where context compounds errors
      log_prob_threshold=-1.0: allow all segments through
        (we do our own confidence filtering)
      no_speech_threshold=0.6: skip segments likely to be silence
    """
    model = _get_whisper_model()

    start_time = time.time()

    try:
        segments, info = model.transcribe(
            audio_path,
            beam_size=5,
            word_timestamps=True,
            language="en",
            condition_on_previous_text=False,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=settings.min_pause_ms,
                threshold=0.5,
            ),
            no_speech_threshold=0.6,
            log_prob_threshold=-1.0,
            temperature=0.0,     # greedy decoding - faster, more consistent
        )

        # Collect all words from all segments
        all_words: List[WordToken] = []
        full_transcript_parts = []

        for segment in segments:
            full_transcript_parts.append(segment.text.strip())

            if segment.words:
                for w in segment.words:
                    all_words.append(WordToken(
                        word=w.word.strip(),
                        start=w.start,
                        end=w.end,
                        confidence=w.probability,
                    ))

        inference_time = time.time() - start_time
        full_transcript = " ".join(full_transcript_parts).strip()

        if not all_words:
            logger.warning(f"[{job_id}] No words transcribed - audio may be silent")
            return TranscriptResult(
                success=False,
                transcript="",
                error_message="No speech detected in audio"
            )

        # Calculate mean confidence
        mean_confidence = sum(w.confidence for w in all_words) / len(all_words)

        # Flag low-confidence words (below 0.5 as per BRD)
        low_confidence_words = [w for w in all_words if w.confidence < 0.5]

        logger.info(
            f"[{job_id}] Transcribed {len(all_words)} words in {inference_time:.1f}s | "
            f"Mean confidence: {mean_confidence:.2f} | "
            f"Low-conf words: {len(low_confidence_words)}"
        )

        return TranscriptResult(
            success=True,
            transcript=full_transcript,
            words=all_words,
            language=info.language,
            language_probability=info.language_probability,
            mean_confidence=mean_confidence,
            low_confidence_words=low_confidence_words,
            duration=info.duration,
            inference_time=inference_time,
            used_fallback=False,
        )

    except RuntimeError as e:
        # Catch GPU OOM and other runtime errors
        if "out of memory" in str(e).lower():
            logger.error(f"[{job_id}] GPU OOM during transcription")
            raise MemoryError("GPU out of memory") from e
        raise


def transcribe(
    audio_path: str,
    job_id: Optional[str] = None,
) -> TranscriptResult:
    """
    Main transcription entry point.
    Automatically handles circuit breaker logic.

    Flow:
      1. Check circuit breaker state
      2. If CLOSED/HALF_OPEN -> try local faster-whisper
      3. If local succeeds with good confidence -> return result
      4. If local fails or low confidence -> record failure, try cloud
      5. If circuit OPEN -> go directly to cloud
    """
    job_id = job_id or "asr"
    circuit = get_circuit_breaker()

    # Check if we should skip local model
    if circuit.should_use_fallback():
        logger.warning(
            f"[{job_id}] Circuit breaker OPEN - routing to cloud API "
            f"(status: {circuit.get_status()})"
        )
        return _run_cloud_fallback(audio_path, job_id)

    # Try local model
    try:
        logger.info(f"[{job_id}] Starting local ASR transcription")
        result = _transcribe_local(audio_path, job_id)

        if result.success:
            # Record success with confidence (circuit breaker monitors this)
            circuit.record_success(result.mean_confidence)
            logger.success(
                f"[{job_id}] ASR complete: {len(result.words)} words | "
                f"confidence: {result.mean_confidence:.2f} | "
                f"time: {result.inference_time:.1f}s"
            )
            return result
        else:
            circuit.record_failure(reason="no_speech_detected")
            return result

    except MemoryError:
        circuit.record_failure(reason="gpu_oom")
        logger.error(f"[{job_id}] GPU OOM - trying cloud fallback")
        return _run_cloud_fallback(audio_path, job_id)

    except Exception as e:
        circuit.record_failure(reason=str(e)[:50])
        logger.error(f"[{job_id}] Local ASR failed: {e}")
        return _run_cloud_fallback(audio_path, job_id)


def _run_cloud_fallback(audio_path: str, job_id: str) -> TranscriptResult:
    """
    Synchronous wrapper for the async cloud fallback.
    Celery workers are synchronous, so we run async code in a new event loop.
    """
    import asyncio
    from src.analysis.asr.fallback import transcribe_with_cloud

    logger.warning(f"[{job_id}] Attempting cloud ASR fallback")

    try:
        loop = asyncio.new_event_loop()
        fallback_result = loop.run_until_complete(
            transcribe_with_cloud(audio_path)
        )
        loop.close()

        if fallback_result.success:
            # Convert fallback result to TranscriptResult format
            words = [
                WordToken(
                    word=w.word,
                    start=w.start,
                    end=w.end,
                    confidence=w.confidence,
                )
                for w in fallback_result.words
            ]
            return TranscriptResult(
                success=True,
                transcript=fallback_result.transcript,
                words=words,
                language=fallback_result.language,
                mean_confidence=fallback_result.mean_confidence,
                low_confidence_words=[w for w in words if w.confidence < 0.5],
                used_fallback=True,
            )
        else:
            return TranscriptResult(
                success=False,
                transcript="",
                error_message=f"Both local and cloud ASR failed: {fallback_result.error_message}",
                used_fallback=True,
            )

    except Exception as e:
        return TranscriptResult(
            success=False,
            transcript="",
            error_message=f"Cloud fallback exception: {e}",
            used_fallback=True,
        )