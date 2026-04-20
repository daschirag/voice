import os
import sys
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import parselmouth
from dataclasses import dataclass
from typing import Optional
from src.core.logger import logger

SENTIMENT_LABELS = {
    "LABEL_0": "negative",
    "LABEL_1": "neutral",
    "LABEL_2": "positive",
}

_sentiment_pipeline = None


def _get_sentiment_pipeline():
    global _sentiment_pipeline
    if _sentiment_pipeline is not None:
        return _sentiment_pipeline

    try:
        # Force torch import first before transformers
        import torch
        import transformers
        transformers.logging.set_verbosity_error()

        from transformers import (
            pipeline,
            AutoTokenizer,
            AutoModelForSequenceClassification,
        )

        logger.info("Loading RoBERTa sentiment model on GPU...")
        model_name = "cardiffnlp/twitter-roberta-base-sentiment"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)

        device = 0 if torch.cuda.is_available() else -1
        _sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model=model,
            tokenizer=tokenizer,
            device=device,
            truncation=True,
            max_length=512,
        )
        logger.success(f"RoBERTa loaded on {'GPU' if device == 0 else 'CPU'}")

    except Exception as e:
        logger.warning(f"RoBERTa load failed: {e} - using VADER fallback")
        _sentiment_pipeline = "vader"

    return _sentiment_pipeline


@dataclass
class PitchMetrics:
    mean_f0: float
    f0_std: float
    f0_range: float
    f0_min: float
    f0_max: float
    voiced_fraction: float


@dataclass
class ToneResult:
    score: float
    tone_class: str
    pitch_metrics: PitchMetrics
    sentiment: str
    sentiment_score: float
    wpm_variance: float
    insight: str = ""


def _extract_pitch_metrics(audio_path: str) -> PitchMetrics:
    try:
        snd = parselmouth.Sound(audio_path)
        pitch = snd.to_pitch(
            time_step=0.01,
            pitch_floor=75.0,
            pitch_ceiling=500.0,
        )
        f0_values = pitch.selected_array["frequency"]
        voiced_f0 = f0_values[f0_values > 0]

        if len(voiced_f0) < 10:
            logger.warning("Insufficient voiced frames for pitch analysis")
            return PitchMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        voiced_fraction = len(voiced_f0) / len(f0_values) if len(f0_values) > 0 else 0
        return PitchMetrics(
            mean_f0=round(float(np.mean(voiced_f0)), 2),
            f0_std=round(float(np.std(voiced_f0)), 2),
            f0_range=round(float(np.max(voiced_f0) - np.min(voiced_f0)), 2),
            f0_min=round(float(np.min(voiced_f0)), 2),
            f0_max=round(float(np.max(voiced_f0)), 2),
            voiced_fraction=round(voiced_fraction, 3),
        )
    except Exception as e:
        logger.error(f"Pitch extraction failed: {e}")
        return PitchMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def _analyze_sentiment(transcript: str) -> tuple:
    if not transcript:
        return "neutral", 0.5

    pipe = _get_sentiment_pipeline()

    if pipe == "vader":
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            analyzer = SentimentIntensityAnalyzer()
            scores = analyzer.polarity_scores(transcript)
            compound = scores["compound"]
            if compound >= 0.05:
                return "positive", abs(compound)
            elif compound <= -0.05:
                return "negative", abs(compound)
            else:
                return "neutral", 1 - abs(compound)
        except Exception:
            return "neutral", 0.5

    if pipe is None:
        return "neutral", 0.5

    try:
        sample = transcript[:1000]
        result = pipe(sample)[0]
        label = SENTIMENT_LABELS.get(result["label"], "neutral")
        return label, result["score"]
    except Exception as e:
        logger.warning(f"Sentiment inference failed: {e}")
        return "neutral", 0.5


def _classify_tone(pitch, sentiment, sentiment_score, wpm_variance):
    f0_std = pitch.f0_std
    f0_range = pitch.f0_range

    if f0_std < 20.0 and pitch.voiced_fraction > 0.1:
        return ("Monotone", 2.0,
                "Your pitch barely varies causing listener fatigue. "
                "Practise reading aloud with exaggerated intonation.")
    if wpm_variance > 30 and sentiment in ("negative", "neutral"):
        return ("Nervous", 2.0,
                "Erratic pacing and hesitant tone detected. "
                "Slow your breathing before speaking.")
    if f0_range > 100 and sentiment == "positive":
        return ("Energetic", 5.0,
                "Highly energetic and engaging delivery. "
                "Excellent for motivational presentations.")
    if f0_std > 40 and sentiment == "positive":
        return ("Friendly", 5.0,
                "Warm approachable tone that builds rapport. "
                "Ideal for client-facing conversations.")
    if 20 <= f0_std <= 40 and sentiment == "neutral":
        return ("Formal", 4.0,
                "Controlled professional tone appropriate for "
                "executive presentations and formal briefings.")
    if sentiment == "positive":
        return ("Friendly", 4.0,
                "Positive tone detected. Add more pitch variation "
                "to make delivery more engaging.")
    elif sentiment == "negative":
        return ("Nervous", 2.0,
                "Negative or hesitant tone detected. "
                "Focus on positive framing and confident body language.")
    else:
        return ("Formal", 3.0,
                "Neutral tone. Add warmth through pitch variation "
                "and positive language to improve listener connection.")


def analyze_tone(
    audio_path: str,
    transcript: str,
    wpm_variance: float = 0.0,
    job_id: Optional[str] = None,
) -> ToneResult:
    job_id = job_id or "tone"
    logger.info(f"[{job_id}] Starting tone analysis")

    pitch_metrics = _extract_pitch_metrics(audio_path)
    logger.debug(
        f"[{job_id}] Pitch: mean={pitch_metrics.mean_f0:.0f}Hz "
        f"SD={pitch_metrics.f0_std:.1f}Hz range={pitch_metrics.f0_range:.0f}Hz"
    )

    sentiment, sentiment_score = _analyze_sentiment(transcript)
    logger.debug(f"[{job_id}] Sentiment: {sentiment} ({sentiment_score:.2f})")

    tone_class, score, insight = _classify_tone(
        pitch_metrics, sentiment, sentiment_score, wpm_variance
    )
    logger.info(f"[{job_id}] Tone: {tone_class} (score {score})")

    return ToneResult(
        score=score,
        tone_class=tone_class,
        pitch_metrics=pitch_metrics,
        sentiment=sentiment,
        sentiment_score=round(sentiment_score, 3),
        wpm_variance=wpm_variance,
        insight=insight,
    )