"""
Punctuation Use Module
----------------------
Maps micro-pauses (150-400ms) to syntactic clause boundaries.
Fixed: uses sentence-end positions from spaCy sentences iterator.
"""
from dataclasses import dataclass, field
from typing import List, Optional
import spacy
from src.analysis.audio_dsp.vad import VADResult
from src.core.logger import logger

_nlp = None

def _get_nlp():
    global _nlp
    if _nlp is None:
        logger.info("Loading spaCy en_core_web_sm...")
        _nlp = spacy.load("en_core_web_sm")
        logger.info("spaCy loaded")
    return _nlp


@dataclass
class PunctuationResult:
    score: float
    placement_ratio: float
    total_clause_boundaries: int
    correctly_placed_pauses: int
    missed_boundaries: List[dict] = field(default_factory=list)
    insight: str = ""


def _get_boundary_word_indices(transcript: str) -> List[int]:
    """
    Return indices of words that are at sentence/clause boundaries.
    Uses spaCy sentence segmentation.
    """
    nlp = _get_nlp()
    doc = nlp(transcript)
    boundary_indices = []

    words = transcript.split()
    word_idx = 0
    char_pos = 0

    for sent in doc.sents:
        # Find the last word of this sentence
        sent_end_char = sent.end_char
        # Walk through words to find which word ends near sent_end_char
        cumulative = 0
        for i, word in enumerate(words):
            cumulative += len(word) + 1  # +1 for space
            if cumulative >= sent_end_char - 5:
                boundary_indices.append(i)
                break

    return boundary_indices


def analyze_punctuation(
    transcript: str,
    words: list,
    vad_result: VADResult,
    job_id: Optional[str] = None,
) -> PunctuationResult:
    """
    Map micro-pauses to clause boundaries from spaCy.
    A pause is 'correctly placed' if it occurs within
    300ms after a sentence boundary word ends.
    """
    job_id = job_id or "punct"

    if not transcript or not words:
        return PunctuationResult(
            score=1.0,
            placement_ratio=0.0,
            total_clause_boundaries=0,
            correctly_placed_pauses=0,
            insight="No transcript available."
        )

    nlp = _get_nlp()
    doc = nlp(transcript)

    # Get sentence boundary timestamps
    # Match each sentence end to the nearest word timestamp
    boundary_times = []
    word_texts_lower = [w.word.lower().strip(".,!?;:\"'") for w in words]

    for sent in doc.sents:
        # Get last meaningful token of sentence
        last_tokens = [t for t in sent if not t.is_space and not t.is_punct]
        if not last_tokens:
            continue
        last_word = last_tokens[-1].text.lower().strip(".,!?;:\"'")

        # Find this word in our timestamped words list
        for i, w_text in enumerate(word_texts_lower):
            if w_text == last_word or last_word in w_text or w_text in last_word:
                if i < len(words):
                    boundary_times.append(words[i].end)
                break

    # Also add comma-based boundaries (mid-sentence pauses)
    for token in doc:
        if token.text == "," and token.i > 0:
            prev_token = doc[token.i - 1]
            prev_word = prev_token.text.lower().strip(".,!?;:\"'")
            for i, w_text in enumerate(word_texts_lower):
                if w_text == prev_word and i < len(words):
                    boundary_times.append(words[i].end)
                    break

    total_boundaries = len(boundary_times)

    if total_boundaries == 0:
        return PunctuationResult(
            score=3.0,
            placement_ratio=0.5,
            total_clause_boundaries=0,
            correctly_placed_pauses=0,
            insight="Could not detect clause boundaries. "
                    "Speak in complete structured sentences."
        )

    # Check how many boundaries have a pause within tolerance
    all_pause_starts = [p.start for p in vad_result.all_pauses]
    tolerance = 0.35   # 350ms tolerance window

    correctly_placed = 0
    missed = []

    for bt in boundary_times:
        found = any(abs(ps - bt) <= tolerance for ps in all_pause_starts)
        if found:
            correctly_placed += 1
        else:
            missed.append({"boundary_time": round(bt, 2)})

    placement_ratio = correctly_placed / total_boundaries if total_boundaries > 0 else 0

    if placement_ratio >= 0.8:
        score = 5.0
        insight = ("Excellent punctuation use. Pauses consistently "
                   "align with clause boundaries.")
    elif placement_ratio >= 0.6:
        score = 4.0
        insight = ("Good punctuation placement. Record yourself and "
                   "mark where commas and periods should fall.")
    elif placement_ratio >= 0.4:
        score = 3.0
        insight = ("Inconsistent punctuation pausing. Practise reading "
                   "aloud with exaggerated pauses at every punctuation mark.")
    elif placement_ratio >= 0.2:
        score = 2.0
        insight = ("Pauses rarely align with clause boundaries. "
                   "Slow down and breathe at each sentence end.")
    else:
        score = 1.0
        insight = ("No meaningful pause-to-boundary alignment. "
                   "Speak one complete thought at a time.")

    logger.debug(
        f"[{job_id}] Punctuation: {correctly_placed}/{total_boundaries} "
        f"({placement_ratio:.2f}) -> score {score}"
    )

    return PunctuationResult(
        score=score,
        placement_ratio=round(placement_ratio, 3),
        total_clause_boundaries=total_boundaries,
        correctly_placed_pauses=correctly_placed,
        missed_boundaries=missed[:10],
        insight=insight,
    )