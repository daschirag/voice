"""
Pauses Module
-------------
Evaluates pause patterns from VAD output.
Ideal professional speech: 4-8 pauses/min, 0.5-1.5s duration.

Scoring combines pause frequency AND mean duration:
  Ideal range (4-8/min, 0.5-1.5s avg) -> 5
  Slightly off                          -> 3-4
  Too frequent (>15/min) or too long    -> 1-2
"""
from dataclasses import dataclass, field
from typing import List, Optional
from src.analysis.audio_dsp.vad import VADResult, PauseSegment
from src.core.logger import logger


@dataclass
class PauseMetrics:
    total_pauses: int
    macro_pause_count: int
    micro_pause_count: int
    pause_frequency_per_min: float
    mean_pause_duration: float
    max_pause_duration: float
    total_silence_seconds: float
    speech_ratio: float         # net speech / total duration


@dataclass
class PauseResult:
    score: float
    metrics: PauseMetrics
    long_pauses: List[dict] = field(default_factory=list)   # pauses > 2s
    insight: str = ""


def analyze_pauses(
    vad_result: VADResult,
    job_id: Optional[str] = None,
) -> PauseResult:
    """
    Score pause patterns based on frequency and duration.

    From BRD 6.2.1:
    Ideal = 4-8 pauses/min of 0.5-1.5s duration -> score 5
    Excessive (> 2s average) or very high frequency (> 15/min) -> low score
    """
    job_id = job_id or "pauses"

    macro_pauses = vad_result.macro_pauses
    total_duration = vad_result.total_duration
    net_speech = vad_result.net_speech_duration

    # Flag pauses longer than 2 seconds (per BRD)
    long_pauses = [
        {
            "start": round(p.start, 2),
            "end": round(p.end, 2),
            "duration": round(p.duration, 2),
        }
        for p in macro_pauses if p.duration > 2.0
    ]

    total_silence = sum(p.duration for p in vad_result.all_pauses)
    speech_ratio = net_speech / total_duration if total_duration > 0 else 0

    metrics = PauseMetrics(
        total_pauses=len(vad_result.all_pauses),
        macro_pause_count=len(macro_pauses),
        micro_pause_count=len(vad_result.micro_pauses),
        pause_frequency_per_min=vad_result.pause_frequency_per_min,
        mean_pause_duration=vad_result.mean_pause_duration,
        max_pause_duration=max((p.duration for p in macro_pauses), default=0.0),
        total_silence_seconds=round(total_silence, 2),
        speech_ratio=round(speech_ratio, 3),
    )

    freq = vad_result.pause_frequency_per_min
    mean_dur = vad_result.mean_pause_duration

    # Scoring logic combining frequency and duration
    freq_ok = 4.0 <= freq <= 8.0
    dur_ok = 0.5 <= mean_dur <= 1.5
    freq_high = freq > 15.0
    freq_low = freq < 2.0
    dur_long = mean_dur > 2.0
    dur_short = mean_dur < 0.3 and freq > 0

    if freq_ok and dur_ok:
        score = 5.0
        insight = ("Excellent pause patterns. Your deliberate pauses project "
                   "confidence and give listeners time to absorb key points.")
    elif (3.0 <= freq <= 10.0) and (0.4 <= mean_dur <= 2.0):
        score = 4.0
        insight = ("Good pause usage with minor deviations from ideal. "
                   "Aim for pauses of 0.5-1.5 seconds at clause boundaries.")
    elif freq_high or dur_long:
        score = 2.0
        if freq_high:
            insight = ("Too many pauses are fragmenting your speech and "
                       "reducing listener confidence. Practise delivering "
                       "complete thoughts without stopping.")
        else:
            insight = ("Pauses are too long (averaging over 2 seconds). "
                       "Prepare key points in advance to reduce hesitation gaps.")
    elif freq_low:
        score = 3.0
        insight = ("You are not pausing enough. Add deliberate 1-second pauses "
                   "at clause boundaries and after key statements to aid comprehension.")
    else:
        score = 3.0
        insight = ("Pause patterns are inconsistent. Record yourself and "
                   "mark clause boundaries to practise deliberate pausing.")

    logger.debug(
        f"[{job_id}] Pauses: freq={freq:.1f}/min mean={mean_dur:.2f}s "
        f"-> score {score}"
    )

    return PauseResult(
        score=score,
        metrics=metrics,
        long_pauses=long_pauses,
        insight=insight,
    )