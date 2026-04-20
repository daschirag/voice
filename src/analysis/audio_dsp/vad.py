import torch
import numpy as np
import soundfile as sf
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from src.core.config import settings
from src.core.logger import logger


# ─────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────

@dataclass
class SpeechSegment:
    """A segment of detected speech."""
    start: float   # seconds
    end: float     # seconds

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class PauseSegment:
    """A detected pause/silence segment."""
    start: float        # seconds
    end: float          # seconds
    pause_type: str     # "micro" (150-400ms) or "macro" (>500ms)

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class VADResult:
    """Complete output from VAD analysis."""
    success: bool
    audio_path: str
    total_duration: float           # total clip duration in seconds
    net_speech_duration: float      # total speaking time (excl. pauses)
    speech_segments: List[SpeechSegment] = field(default_factory=list)
    all_pauses: List[PauseSegment] = field(default_factory=list)
    micro_pauses: List[PauseSegment] = field(default_factory=list)  # 150-400ms
    macro_pauses: List[PauseSegment] = field(default_factory=list)  # >500ms
    pause_frequency_per_min: float = 0.0   # macro pauses per minute of speech
    mean_pause_duration: float = 0.0       # mean macro pause duration in seconds
    error_message: Optional[str] = None


# ─────────────────────────────────────────────
# Silero VAD Loader (cached singleton)
# ─────────────────────────────────────────────

_silero_model = None
_silero_utils = None

def _get_silero_model():
    """
    Load Silero VAD model once and cache it.
    Why singleton? Loading the model takes ~2 seconds.
    Caching means the 2nd call is instant.
    """
    global _silero_model, _silero_utils

    if _silero_model is not None:
        return _silero_model, _silero_utils

    logger.info("Loading Silero VAD model...")
    try:
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            trust_repo=True,
        )
        _silero_model = model
        _silero_utils = utils
        logger.info("Silero VAD model loaded successfully")
        return _silero_model, _silero_utils

    except Exception as e:
        logger.error(f"Failed to load Silero VAD: {e}")
        raise


# ─────────────────────────────────────────────
# Core VAD Functions
# ─────────────────────────────────────────────

def _load_audio_for_vad(audio_path: str) -> Tuple[torch.Tensor, int]:
    """
    Load a 16kHz mono WAV into a torch tensor for Silero VAD.
    Silero requires: float32 tensor, 16kHz, mono, values in [-1, 1].
    """
    audio_np, sample_rate = sf.read(audio_path, dtype="float32")

    # Ensure mono
    if audio_np.ndim > 1:
        audio_np = np.mean(audio_np, axis=1)

    # Convert to torch tensor
    audio_tensor = torch.from_numpy(audio_np)

    return audio_tensor, sample_rate


def _run_silero_vad(
    audio_tensor: torch.Tensor,
    sample_rate: int,
    min_silence_duration_ms: int = 150,
    min_speech_duration_ms: int = 100,
    threshold: float = 0.5,
) -> List[dict]:
    """
    Run Silero VAD and return speech timestamps.

    Args:
        audio_tensor: 1D float32 torch tensor
        sample_rate: must be 16000
        min_silence_duration_ms: minimum silence to count as pause (150ms per BRD)
        min_speech_duration_ms: minimum speech chunk to keep
        threshold: VAD confidence threshold (0.5 = balanced precision/recall)

    Returns:
        List of dicts: [{"start": float, "end": float}, ...]
        Each dict is a speech segment in seconds.
    """
    model, utils = _get_silero_model()
    get_speech_timestamps = utils[0]

    speech_timestamps = get_speech_timestamps(
        audio_tensor,
        model,
        sampling_rate=sample_rate,
        threshold=threshold,
        min_silence_duration_ms=min_silence_duration_ms,
        min_speech_duration_ms=min_speech_duration_ms,
        return_seconds=True,    # return timestamps in seconds not samples
    )

    return speech_timestamps


def _extract_pauses(
    speech_segments: List[SpeechSegment],
    total_duration: float,
    min_pause_ms: int = 150,
) -> Tuple[List[PauseSegment], List[PauseSegment], List[PauseSegment]]:
    """
    Derive pause segments from the gaps between speech segments.

    Pause classification (from BRD section 6.2):
      - micro pause: 150ms - 400ms  (used for punctuation mapping)
      - macro pause: >500ms         (used for pause pattern scoring)
      - gap 400-500ms: transitional (counted but not classified strictly)

    Args:
        speech_segments: list of detected speech segments
        total_duration: total audio duration in seconds
        min_pause_ms: minimum duration to consider a gap a pause

    Returns:
        (all_pauses, micro_pauses, macro_pauses)
    """
    all_pauses = []
    micro_pauses = []
    macro_pauses = []

    min_pause_sec = min_pause_ms / 1000.0
    micro_max_sec = 0.400   # 400ms upper bound for micro pauses
    macro_min_sec = 0.500   # 500ms lower bound for macro pauses

    # Check for silence BEFORE first speech segment
    if speech_segments and speech_segments[0].start > min_pause_sec:
        pause = PauseSegment(
            start=0.0,
            end=speech_segments[0].start,
            pause_type="macro" if speech_segments[0].start >= macro_min_sec else "micro"
        )
        all_pauses.append(pause)

    # Check gaps BETWEEN speech segments
    for i in range(len(speech_segments) - 1):
        gap_start = speech_segments[i].end
        gap_end = speech_segments[i + 1].start
        gap_duration = gap_end - gap_start

        if gap_duration >= min_pause_sec:
            if gap_duration <= micro_max_sec:
                pause_type = "micro"
            elif gap_duration >= macro_min_sec:
                pause_type = "macro"
            else:
                # 400-500ms transitional zone - classify as micro
                pause_type = "micro"

            pause = PauseSegment(
                start=gap_start,
                end=gap_end,
                pause_type=pause_type
            )
            all_pauses.append(pause)

    # Check for silence AFTER last speech segment
    if speech_segments and total_duration - speech_segments[-1].end > min_pause_sec:
        trailing_gap = total_duration - speech_segments[-1].end
        pause = PauseSegment(
            start=speech_segments[-1].end,
            end=total_duration,
            pause_type="macro" if trailing_gap >= macro_min_sec else "micro"
        )
        all_pauses.append(pause)

    # Split into micro and macro lists
    micro_pauses = [p for p in all_pauses if p.pause_type == "micro"]
    macro_pauses = [p for p in all_pauses if p.pause_type == "macro"]

    return all_pauses, micro_pauses, macro_pauses


def _calculate_pause_metrics(
    macro_pauses: List[PauseSegment],
    net_speech_duration: float,
) -> Tuple[float, float]:
    """
    Calculate pause frequency and mean pause duration.

    pause_frequency = macro pauses per minute of NET speech
    mean_pause_duration = average macro pause length in seconds

    Why use net speech duration (not total)?
    Because we want to measure how often the speaker pauses
    WHILE SPEAKING, not including silence before/after the clip.
    """
    if not macro_pauses or net_speech_duration <= 0:
        return 0.0, 0.0

    speech_minutes = net_speech_duration / 60.0
    pause_frequency = len(macro_pauses) / speech_minutes if speech_minutes > 0 else 0.0
    mean_duration = np.mean([p.duration for p in macro_pauses])

    return float(pause_frequency), float(mean_duration)


# ─────────────────────────────────────────────
# Main VAD Function
# ─────────────────────────────────────────────

def analyze_vad(
    audio_path: str,
    job_id: Optional[str] = None,
) -> VADResult:
    """
    Run complete VAD analysis on a preprocessed 16kHz mono WAV.

    Args:
        audio_path: path to preprocessed 16kHz mono WAV file
        job_id: for logging correlation

    Returns:
        VADResult with all speech/pause segments and metrics
    """
    import os
    job_id = job_id or "vad"

    if not os.path.exists(audio_path):
        return VADResult(
            success=False,
            audio_path=audio_path,
            total_duration=0.0,
            net_speech_duration=0.0,
            error_message=f"Audio file not found: {audio_path}"
        )

    logger.info(f"[{job_id}] Starting VAD analysis")

    try:
        # Step 1: Load audio
        audio_tensor, sample_rate = _load_audio_for_vad(audio_path)
        total_duration = len(audio_tensor) / sample_rate
        logger.debug(f"[{job_id}] Audio loaded: {total_duration:.1f}s at {sample_rate}Hz")

        # Step 2: Run Silero VAD
        raw_timestamps = _run_silero_vad(
            audio_tensor,
            sample_rate,
            min_silence_duration_ms=settings.min_pause_ms,  # 150ms from config
        )
        logger.debug(f"[{job_id}] Silero VAD found {len(raw_timestamps)} speech segments")

        # Step 3: Convert to SpeechSegment objects
        speech_segments = [
            SpeechSegment(start=t["start"], end=t["end"])
            for t in raw_timestamps
        ]

        # Step 4: Calculate net speech duration
        net_speech_duration = sum(s.duration for s in speech_segments)
        logger.info(
            f"[{job_id}] Speech: {net_speech_duration:.1f}s | "
            f"Silence: {total_duration - net_speech_duration:.1f}s | "
            f"Ratio: {net_speech_duration/total_duration*100:.1f}%"
        )

        # Step 5: Extract pauses from gaps between speech
        all_pauses, micro_pauses, macro_pauses = _extract_pauses(
            speech_segments,
            total_duration,
            min_pause_ms=settings.min_pause_ms,
        )
        logger.info(
            f"[{job_id}] Pauses: {len(all_pauses)} total | "
            f"{len(micro_pauses)} micro (150-400ms) | "
            f"{len(macro_pauses)} macro (>500ms)"
        )

        # Step 6: Calculate pause metrics
        pause_frequency, mean_pause_dur = _calculate_pause_metrics(
            macro_pauses,
            net_speech_duration,
        )
        logger.info(
            f"[{job_id}] Pause freq: {pause_frequency:.1f}/min | "
            f"Mean duration: {mean_pause_dur:.2f}s"
        )

        logger.success(f"[{job_id}] VAD analysis complete")

        return VADResult(
            success=True,
            audio_path=audio_path,
            total_duration=total_duration,
            net_speech_duration=net_speech_duration,
            speech_segments=speech_segments,
            all_pauses=all_pauses,
            micro_pauses=micro_pauses,
            macro_pauses=macro_pauses,
            pause_frequency_per_min=pause_frequency,
            mean_pause_duration=mean_pause_dur,
        )

    except Exception as e:
        logger.error(f"[{job_id}] VAD analysis failed: {e}")
        return VADResult(
            success=False,
            audio_path=audio_path,
            total_duration=0.0,
            net_speech_duration=0.0,
            error_message=str(e)
        )