"""
Filler Words Module
-------------------
Detects filler words using exact token matching (regex).
Why not NER/LLM? Fillers are a closed-class lexicon.
Regex is 100% precise relative to ASR output and computationally free.

Score bands (from BRD 6.2.1):
  0 fillers per 100 words     -> 5
  1-4 per 100 words           -> 4
  5-9 per 100 words           -> 3
  10-14 per 100 words         -> 2
  >= 15 per 100 words         -> 1
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from src.analysis.asr.transcriber import WordToken
from src.core.logger import logger

# Default filler word list from BRD 6.2.1
# Configurable - can be extended per client
DEFAULT_FILLERS = {
    "um", "uh", "like", "you know", "basically",
    "literally", "right", "so", "okay", "well",
    "actually", "honestly", "I mean", "kind of",
    "sort of", "you see",
}


@dataclass
class FillerOccurrence:
    word: str
    start: float
    end: float
    context: str    # surrounding words for report


@dataclass
class FillerResult:
    score: float
    filler_rate_per_100: float          # fillers per 100 words
    total_fillers: int
    total_words: int
    filler_counts: Dict[str, int] = field(default_factory=dict)
    occurrences: List[FillerOccurrence] = field(default_factory=list)
    insight: str = ""


def analyze_filler_words(
    words: List[WordToken],
    transcript: str,
    custom_fillers: Optional[set] = None,
    job_id: Optional[str] = None,
) -> FillerResult:
    """
    Detect filler words in the transcript using token matching.

    Uses word-level tokens from ASR output for precise timestamps.
    Multi-word fillers (e.g. "you know") are detected in transcript text.
    """
    job_id = job_id or "filler"

    fillers = custom_fillers or DEFAULT_FILLERS
    total_words = len(words)

    if total_words == 0:
        return FillerResult(
            score=1.0,
            filler_rate_per_100=0.0,
            total_fillers=0,
            total_words=0,
            insight="No words to analyze."
        )

    # Build word list for context lookup
    word_texts = [w.word.lower().strip(".,!?;:") for w in words]
    filler_counts: Dict[str, int] = {}
    occurrences: List[FillerOccurrence] = []

    # Check each word position against filler list
    i = 0
    while i < len(words):
        matched = False

        # Check multi-word fillers first (longest match)
        for filler in sorted(fillers, key=len, reverse=True):
            filler_tokens = filler.lower().split()
            n = len(filler_tokens)

            if i + n <= len(word_texts):
                window = word_texts[i:i + n]
                if window == filler_tokens:
                    # Build context (3 words before and after)
                    ctx_start = max(0, i - 3)
                    ctx_end = min(len(words), i + n + 3)
                    context_words = [w.word for w in words[ctx_start:ctx_end]]
                    context = " ".join(context_words)

                    occurrence = FillerOccurrence(
                        word=filler,
                        start=words[i].start,
                        end=words[i + n - 1].end,
                        context=context,
                    )
                    occurrences.append(occurrence)
                    filler_counts[filler] = filler_counts.get(filler, 0) + 1
                    i += n
                    matched = True
                    break

        if not matched:
            i += 1

    total_fillers = sum(filler_counts.values())
    filler_rate = (total_fillers / total_words) * 100 if total_words > 0 else 0

    # Score bands from BRD
    if filler_rate == 0:
        score = 5.0
        insight = ("Outstanding. No filler words detected. "
                   "Your speech is clean and professional.")
    elif filler_rate < 5:
        score = 4.0
        insight = ("Good filler word control with minor occurrences. "
                   "Replace remaining fillers with a deliberate 1-second pause instead.")
    elif filler_rate < 10:
        score = 3.0
        insight = ("Moderate filler word usage. Before speaking, "
                   "pause and collect your thought rather than filling silence with words.")
    elif filler_rate < 15:
        score = 2.0
        insight = ("High filler word usage is reducing your credibility. "
                   "Record yourself daily and count fillers to build awareness.")
    else:
        score = 1.0
        insight = ("Filler words are significantly impacting your professional presence. "
                   "Practice the pause: when you feel a filler coming, stay silent for 1 second.")

    logger.debug(
        f"[{job_id}] Fillers: {total_fillers} ({filler_rate:.1f}/100 words) "
        f"-> score {score}"
    )

    return FillerResult(
        score=score,
        filler_rate_per_100=round(filler_rate, 2),
        total_fillers=total_fillers,
        total_words=total_words,
        filler_counts=filler_counts,
        occurrences=occurrences,
        insight=insight,
    )