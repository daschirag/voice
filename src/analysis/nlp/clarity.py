"""
Clarity Module
--------------
Measures how clearly the speaker articulates words.
Signal: ASR word-level confidence scores.

Score bands (from BRD 6.2.1):
  < 70%  -> 1
  70-79% -> 2
  80-87% -> 3
  88-94% -> 4
  >= 95% -> 5
"""
from dataclasses import dataclass, field
from typing import List, Optional
from src.analysis.asr.transcriber import WordToken
from src.core.logger import logger


@dataclass
class ClarityResult:
    score: float                              # 1.0 to 5.0
    mean_confidence_pct: float                # 0 to 100
    total_words: int
    low_confidence_words: List[dict] = field(default_factory=list)
    insight: str = ""


def analyze_clarity(
    words: List[WordToken],
    job_id: Optional[str] = None,
) -> ClarityResult:
    """
    Calculate clarity score from ASR word confidence scores.

    Low confidence words (< 0.5) are flagged with their
    timestamps so the report can highlight them.
    """
    job_id = job_id or "clarity"

    if not words:
        return ClarityResult(
            score=1.0,
            mean_confidence_pct=0.0,
            total_words=0,
            insight="No speech detected. Please submit a clip with audible speech."
        )

    # Calculate mean confidence across all words
    mean_conf = sum(w.confidence for w in words) / len(words)
    mean_conf_pct = mean_conf * 100

    # Flag words with confidence below 0.5 (per BRD 6.2.1)
    low_conf_words = [
        {
            "word": w.word,
            "start": round(w.start, 2),
            "end": round(w.end, 2),
            "confidence": round(w.confidence, 3),
        }
        for w in words if w.confidence < 0.5
    ]

    # Score bands from BRD
    if mean_conf_pct < 70:
        score = 1.0
        insight = ("Your speech clarity needs significant improvement. "
                   "Practise enunciation drills focusing on consonant precision, "
                   "especially word endings like 't', 'd', and 's'.")
    elif mean_conf_pct < 80:
        score = 2.0
        insight = ("Clarity is below average. Slow down slightly and "
                   "open your mouth more when speaking. Record yourself "
                   "and listen for swallowed syllables.")
    elif mean_conf_pct < 88:
        score = 3.0
        insight = ("Clarity is acceptable but inconsistent. Focus on "
                   "maintaining articulation energy throughout sentences, "
                   "not just at the start.")
    elif mean_conf_pct < 95:
        score = 4.0
        insight = ("Good clarity with minor lapses. Review the flagged "
                   "low-confidence words and practise those specific sounds.")
    else:
        score = 5.0
        insight = ("Excellent clarity. Your articulation is consistently "
                   "precise across the entire clip.")

    logger.debug(
        f"[{job_id}] Clarity: {mean_conf_pct:.1f}% -> score {score} | "
        f"{len(low_conf_words)} low-conf words"
    )

    return ClarityResult(
        score=score,
        mean_confidence_pct=round(mean_conf_pct, 2),
        total_words=len(words),
        low_confidence_words=low_conf_words,
        insight=insight,
    )