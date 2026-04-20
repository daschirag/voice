"""
Delivery Quality Module
-----------------------
Measures speech rate (WPM) and rhythm consistency.

Net WPM = total words / net speech minutes (excluding pauses)
Rhythm variance = std dev of WPM in rolling 10-second windows

Score bands (from BRD 6.2.1):
  130-160 WPM, variance < 20  -> 5
  110-130 or 160-180, variance < 30 -> 4
  90-110 or 180-200, variance < 40 -> 3
  Outside 90-200 or variance >= 40 -> 1-2
"""
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional
from src.analysis.asr.transcriber import WordToken
from src.analysis.audio_dsp.vad import VADResult
from src.core.logger import logger


@dataclass
class DeliveryResult:
    score: float
    wpm: float                          # words per minute (net)
    rhythm_variance: float              # std dev of rolling WPM
    total_words: int
    net_speech_duration: float          # seconds
    rolling_wpm_windows: List[float] = field(default_factory=list)
    insight: str = ""


def _calculate_rolling_wpm(
    words: List[WordToken],
    window_seconds: float = 10.0,
) -> List[float]:
    """
    Calculate WPM in rolling 10-second windows.

    Sliding window approach:
    - Move window start forward word by word
    - Count words whose midpoint falls within [window_start, window_start+10s]
    - Convert count to WPM

    Why 10-second windows?
    - Short enough to detect local rhythm changes
    - Long enough to have statistically meaningful word counts
    """
    if not words or words[-1].end < window_seconds:
        return []

    rolling_wpms = []
    total_duration = words[-1].end

    window_start = words[0].start
    while window_start + window_seconds <= total_duration:
        window_end = window_start + window_seconds

        # Count words with midpoint in this window
        count = sum(
            1 for w in words
            if window_start <= (w.start + w.end) / 2 <= window_end
        )
        wpm = (count / window_seconds) * 60
        rolling_wpms.append(wpm)
        window_start += 2.0   # advance by 2 seconds (overlapping windows)

    return rolling_wpms


def analyze_delivery(
    words: List[WordToken],
    vad_result: VADResult,
    job_id: Optional[str] = None,
) -> DeliveryResult:
    """
    Calculate speech rate and rhythm variance.

    Net WPM uses net_speech_duration from VAD (excludes pause time).
    This gives the true speaking rate, not distorted by silence.
    """
    job_id = job_id or "delivery"

    if not words:
        return DeliveryResult(
            score=1.0,
            wpm=0.0,
            rhythm_variance=0.0,
            total_words=0,
            net_speech_duration=0.0,
            insight="No speech detected."
        )

    total_words = len(words)
    net_speech_minutes = vad_result.net_speech_duration / 60.0

    if net_speech_minutes <= 0:
        return DeliveryResult(
            score=1.0,
            wpm=0.0,
            rhythm_variance=0.0,
            total_words=total_words,
            net_speech_duration=0.0,
            insight="Could not calculate speech duration."
        )

    # Net WPM
    wpm = total_words / net_speech_minutes

    # Rhythm variance from rolling windows
    rolling_wpms = _calculate_rolling_wpm(words, window_seconds=10.0)
    rhythm_variance = float(np.std(rolling_wpms)) if len(rolling_wpms) > 1 else 0.0

    # Scoring: WPM range + variance
    wpm_ideal = 130 <= wpm <= 160
    wpm_good = 110 <= wpm <= 180
    wpm_ok = 90 <= wpm <= 200
    var_excellent = rhythm_variance < 20
    var_good = rhythm_variance < 30
    var_ok = rhythm_variance < 40

    if wpm_ideal and var_excellent:
        score = 5.0
        insight = ("Perfect delivery pace and rhythm. "
                   "Your 130-160 WPM rate with consistent rhythm maximises "
                   "listener comprehension and retention.")
    elif wpm_good and var_good:
        score = 4.0
        if wpm > 160:
            insight = ("Slightly fast but controlled. Consciously slow down "
                       "after key statements to let points land.")
        elif wpm < 130:
            insight = ("Slightly slow but steady. Increase energy and pace "
                       "slightly to maintain listener engagement.")
        else:
            insight = ("Good delivery with minor rhythm variations. "
                       "Practise with a metronome at 140 WPM to build consistency.")
    elif wpm_ok and var_ok:
        score = 3.0
        if rhythm_variance >= 30:
            insight = ("Your pace varies significantly. Inconsistent rhythm "
                       "makes it hard for listeners to follow. "
                       "Record at target pace and compare.")
        else:
            insight = ("Speech rate is outside the professional ideal range. "
                       "Target 130-160 WPM: count words in a 30-second recording.")
    elif wpm > 200:
        score = 2.0
        insight = ("Speaking too fast. At this pace, listeners lose comprehension "
                   "after 30 seconds. Practise the pause-breathe-continue technique.")
    elif wpm < 90:
        score = 2.0
        insight = ("Speaking too slowly. This pace may cause listener disengagement. "
                   "Increase energy and reduce pause length between thoughts.")
    else:
        score = 1.0
        insight = ("Delivery needs significant improvement in both pace and rhythm. "
                   "Start with a 60-second timed speech exercise daily.")

    logger.debug(
        f"[{job_id}] Delivery: {wpm:.0f} WPM, variance={rhythm_variance:.1f} "
        f"-> score {score}"
    )

    return DeliveryResult(
        score=score,
        wpm=round(wpm, 1),
        rhythm_variance=round(rhythm_variance, 2),
        total_words=total_words,
        net_speech_duration=round(vad_result.net_speech_duration, 2),
        rolling_wpm_windows=rolling_wpms[:20],   # first 20 windows for report
        insight=insight,
    )