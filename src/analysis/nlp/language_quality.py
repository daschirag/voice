"""
Language Quality Module
-----------------------
Combines Type-Token Ratio (TTR) and Flesch-Kincaid Grade Level.
Uses MATTR (Moving Average TTR) for length-bias resistance.

Weighted score: 0.6 * TTR_score + 0.4 * FK_score

TTR bands:
  >= 0.40 -> 5
  0.35-0.39 -> 4
  0.30-0.34 -> 3
  0.25-0.29 -> 2
  < 0.25  -> 1

FK Grade bands (professional speech target: 8-14):
  8-14  -> 5
  6-7 or 15-16 -> 4
  5 or 17-18   -> 3
  3-4 or 19-20 -> 2
  < 3 or > 20  -> 1
"""
from dataclasses import dataclass
from typing import Optional
import textstat
from lexical_diversity import lex_div as ld
from src.core.logger import logger


@dataclass
class LanguageQualityResult:
    score: float                    # final weighted score 1-5
    ttr_score: float                # 1-5
    fk_score: float                 # 1-5
    mattr_value: float              # raw MATTR value
    fk_grade: float                 # raw Flesch-Kincaid grade
    flesch_reading_ease: float      # raw Flesch reading ease
    total_words: int
    unique_words: int
    insight: str = ""


def _score_mattr(mattr: float) -> float:
    """Convert MATTR value to 1-5 score."""
    if mattr >= 0.40:
        return 5.0
    elif mattr >= 0.35:
        return 4.0
    elif mattr >= 0.30:
        return 3.0
    elif mattr >= 0.25:
        return 2.0
    else:
        return 1.0


def _score_fk_grade(grade: float) -> float:
    """
    Convert Flesch-Kincaid Grade Level to 1-5 score.
    Target for professional speech: grade 8-14.
    Too simple (< 5) or too complex (> 18) are both penalized.
    """
    if 8 <= grade <= 14:
        return 5.0
    elif (6 <= grade < 8) or (14 < grade <= 16):
        return 4.0
    elif (5 <= grade < 6) or (16 < grade <= 18):
        return 3.0
    elif (3 <= grade < 5) or (18 < grade <= 20):
        return 2.0
    else:
        return 1.0


def analyze_language_quality(
    transcript: str,
    job_id: Optional[str] = None,
) -> LanguageQualityResult:
    """
    Analyze vocabulary richness and sentence complexity.

    MATTR (Moving Average TTR):
    - Calculates TTR in a 50-word sliding window
    - Averages across all windows
    - Eliminates length bias (naive TTR decreases with longer texts)

    Flesch-Kincaid Grade Level:
    - Measures sentence complexity
    - Based on syllables per word and words per sentence
    - Target: grade 8-14 for professional spoken English
    """
    job_id = job_id or "language"

    if not transcript or len(transcript.split()) < 10:
        return LanguageQualityResult(
            score=1.0,
            ttr_score=1.0,
            fk_score=1.0,
            mattr_value=0.0,
            fk_grade=0.0,
            flesch_reading_ease=0.0,
            total_words=0,
            unique_words=0,
            insight="Transcript too short for language quality analysis (minimum 10 words)."
        )

    # Tokenize
    words = transcript.lower().split()
    words_clean = [w.strip(".,!?;:\"'") for w in words if w.strip(".,!?;:\"'")]
    total_words = len(words_clean)
    unique_words = len(set(words_clean))

    # Calculate MATTR (window=50 words)
    try:
        # lexical_diversity expects a list of tokens
        mattr_value = ld.mattr(words_clean, window_length=min(50, total_words))
    except Exception as e:
        logger.warning(f"[{job_id}] MATTR calculation failed: {e} - using naive TTR")
        mattr_value = unique_words / total_words if total_words > 0 else 0.0

    # Calculate Flesch-Kincaid Grade Level
    try:
        fk_grade = textstat.flesch_kincaid_grade(transcript)
        flesch_ease = textstat.flesch_reading_ease(transcript)
    except Exception as e:
        logger.warning(f"[{job_id}] Flesch-Kincaid calculation failed: {e}")
        fk_grade = 10.0
        flesch_ease = 60.0

    # Individual scores
    ttr_score = _score_mattr(mattr_value)
    fk_score = _score_fk_grade(fk_grade)

    # Weighted composite (60% TTR, 40% FK per BRD)
    final_score = round(0.6 * ttr_score + 0.4 * fk_score, 2)

    # Build insight
    if final_score >= 4.5:
        insight = ("Excellent language quality. Your vocabulary is rich "
                   "and sentence complexity is appropriate for professional communication.")
    elif final_score >= 3.5:
        insight = ("Good language quality. Expand your vocabulary by "
                   "learning 5 new domain-specific words per week.")
    elif final_score >= 2.5:
        insight = ("Average language quality. Vary your sentence length more "
                   "and replace common words with precise alternatives.")
    else:
        if ttr_score < fk_score:
            insight = ("Vocabulary repetition is high. Avoid reusing the same "
                       "words and phrases. Prepare key synonyms before speaking.")
        else:
            insight = ("Sentence structure needs improvement. Mix short, "
                       "punchy sentences with longer explanatory ones.")

    logger.debug(
        f"[{job_id}] Language: MATTR={mattr_value:.3f}(score {ttr_score}) "
        f"FK={fk_grade:.1f}(score {fk_score}) -> final {final_score}"
    )

    return LanguageQualityResult(
        score=final_score,
        ttr_score=ttr_score,
        fk_score=fk_score,
        mattr_value=round(mattr_value, 4),
        fk_grade=round(fk_grade, 2),
        flesch_reading_ease=round(flesch_ease, 2),
        total_words=total_words,
        unique_words=unique_words,
        insight=insight,
    )