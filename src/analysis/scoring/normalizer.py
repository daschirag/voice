"""
Score Normalizer
----------------
Converts raw dimension scores (already 1-5) into
a standardized format and validates bounds.

Also provides the piecewise linear normalization
function used for composite score calculation.
"""
from dataclasses import dataclass
from typing import Dict
from src.core.logger import logger


@dataclass
class DimensionScore:
    """Standardized score for one dimension."""
    name: str
    raw_score: float        # 1.0 to 5.0
    normalized: float       # 0.0 to 1.0 (for composite calculation)
    insight: str
    raw_metrics: dict       # dimension-specific raw values


def normalize_to_unit(score: float, min_val: float = 1.0, max_val: float = 5.0) -> float:
    """Convert a 1-5 score to 0-1 range for weighted averaging."""
    if max_val == min_val:
        return 0.0
    return max(0.0, min(1.0, (score - min_val) / (max_val - min_val)))


def clamp_score(score: float) -> float:
    """Ensure score is within valid 1-5 range."""
    return max(1.0, min(5.0, round(score, 2)))


def build_dimension_scores(
    clarity_result,
    filler_result,
    pause_result,
    punct_result,
    language_result,
    delivery_result,
    tone_result,
) -> Dict[str, DimensionScore]:
    """
    Package all 7 dimension results into standardized DimensionScore objects.
    Each gets a name, clamped score, normalized value, insight, and raw metrics.
    """
    dimensions = {}

    # 1. Clarity
    dimensions["clarity"] = DimensionScore(
        name="Clarity",
        raw_score=clamp_score(clarity_result.score),
        normalized=normalize_to_unit(clarity_result.score),
        insight=clarity_result.insight,
        raw_metrics={
            "mean_confidence_pct": clarity_result.mean_confidence_pct,
            "total_words": clarity_result.total_words,
            "low_confidence_word_count": len(clarity_result.low_confidence_words),
            "low_confidence_words": clarity_result.low_confidence_words[:5],
        }
    )

    # 2. Filler Words
    dimensions["filler_words"] = DimensionScore(
        name="Filler Words",
        raw_score=clamp_score(filler_result.score),
        normalized=normalize_to_unit(filler_result.score),
        insight=filler_result.insight,
        raw_metrics={
            "filler_rate_per_100": filler_result.filler_rate_per_100,
            "total_fillers": filler_result.total_fillers,
            "total_words": filler_result.total_words,
            "filler_counts": filler_result.filler_counts,
            "occurrences": [
                {"word": o.word, "start": o.start, "end": o.end, "context": o.context}
                for o in filler_result.occurrences[:10]
            ],
        }
    )

    # 3. Pauses
    dimensions["pauses"] = DimensionScore(
        name="Pause Patterns",
        raw_score=clamp_score(pause_result.score),
        normalized=normalize_to_unit(pause_result.score),
        insight=pause_result.insight,
        raw_metrics={
            "pause_frequency_per_min": pause_result.metrics.pause_frequency_per_min,
            "mean_pause_duration": pause_result.metrics.mean_pause_duration,
            "macro_pause_count": pause_result.metrics.macro_pause_count,
            "micro_pause_count": pause_result.metrics.micro_pause_count,
            "speech_ratio": pause_result.metrics.speech_ratio,
            "long_pauses": pause_result.long_pauses[:5],
        }
    )

    # 4. Punctuation
    dimensions["punctuation"] = DimensionScore(
        name="Punctuation Use",
        raw_score=clamp_score(punct_result.score),
        normalized=normalize_to_unit(punct_result.score),
        insight=punct_result.insight,
        raw_metrics={
            "placement_ratio": punct_result.placement_ratio,
            "total_clause_boundaries": punct_result.total_clause_boundaries,
            "correctly_placed_pauses": punct_result.correctly_placed_pauses,
            "missed_boundaries": punct_result.missed_boundaries[:5],
        }
    )

    # 5. Language Quality
    dimensions["language_quality"] = DimensionScore(
        name="Language Quality",
        raw_score=clamp_score(language_result.score),
        normalized=normalize_to_unit(language_result.score),
        insight=language_result.insight,
        raw_metrics={
            "mattr_value": language_result.mattr_value,
            "fk_grade": language_result.fk_grade,
            "flesch_reading_ease": language_result.flesch_reading_ease,
            "total_words": language_result.total_words,
            "unique_words": language_result.unique_words,
            "ttr_score": language_result.ttr_score,
            "fk_score": language_result.fk_score,
        }
    )

    # 6. Delivery
    dimensions["delivery"] = DimensionScore(
        name="Delivery Quality",
        raw_score=clamp_score(delivery_result.score),
        normalized=normalize_to_unit(delivery_result.score),
        insight=delivery_result.insight,
        raw_metrics={
            "wpm": delivery_result.wpm,
            "rhythm_variance": delivery_result.rhythm_variance,
            "total_words": delivery_result.total_words,
            "net_speech_duration": delivery_result.net_speech_duration,
        }
    )

    # 7. Tone
    dimensions["tone"] = DimensionScore(
        name="Tone / Demeanor",
        raw_score=clamp_score(tone_result.score),
        normalized=normalize_to_unit(tone_result.score),
        insight=tone_result.insight,
        raw_metrics={
            "tone_class": tone_result.tone_class,
            "sentiment": tone_result.sentiment,
            "sentiment_score": tone_result.sentiment_score,
            "mean_f0": tone_result.pitch_metrics.mean_f0,
            "f0_std": tone_result.pitch_metrics.f0_std,
            "f0_range": tone_result.pitch_metrics.f0_range,
            "voiced_fraction": tone_result.pitch_metrics.voiced_fraction,
        }
    )

    logger.debug(f"Built {len(dimensions)} dimension scores")
    return dimensions