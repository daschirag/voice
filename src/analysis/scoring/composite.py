"""
Composite Score Calculator
--------------------------
Combines 7 dimension scores into one weighted composite score.
Also generates improvement priorities and summary text.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from src.analysis.scoring.normalizer import DimensionScore
from src.analysis.scoring.weights import get_weights
from src.core.logger import logger


@dataclass
class CompositeResult:
    """Final scoring output for one audio clip."""
    composite_score: float                          # weighted 1-5 score
    composite_pct: float                            # 0-100 percentage
    role: str
    dimensions: Dict[str, DimensionScore]           # all 7 dimension scores
    improvement_priorities: List[str] = field(default_factory=list)
    summary: str = ""
    grade: str = ""                                 # A/B/C/D/F


def _score_to_grade(score: float) -> str:
    """Convert 1-5 score to letter grade."""
    if score >= 4.5:
        return "A"
    elif score >= 3.5:
        return "B"
    elif score >= 2.5:
        return "C"
    elif score >= 1.5:
        return "D"
    else:
        return "F"


def _generate_summary(
    composite: float,
    dimensions: Dict[str, DimensionScore],
    role: str,
) -> str:
    """
    Auto-generate a one-paragraph summary from dimension results.
    Highlights strengths and top improvement area.
    """
    scores = {k: v.raw_score for k, v in dimensions.items()}
    best = max(scores, key=scores.get)
    worst = min(scores, key=scores.get)
    best_name = dimensions[best].name
    worst_name = dimensions[worst].name

    tone_class = dimensions["tone"].raw_metrics.get("tone_class", "neutral")
    wpm = dimensions["delivery"].raw_metrics.get("wpm", 0)
    filler_count = dimensions["filler_words"].raw_metrics.get("total_fillers", 0)

    if composite >= 4.0:
        opening = "This is a strong performance overall."
    elif composite >= 3.0:
        opening = "This is a solid performance with clear areas to develop."
    else:
        opening = "This performance shows foundational areas that need focused attention."

    summary = (
        f"{opening} "
        f"The speaker demonstrates strongest command in {best_name} "
        f"and presents a {tone_class.lower()} tone throughout. "
        f"Speaking at {wpm:.0f} words per minute with {filler_count} filler word(s) detected, "
        f"the primary opportunity for improvement lies in {worst_name}. "
        f"Targeted practice in this dimension will have the highest impact "
        f"on overall communication effectiveness for the {role} context."
    )
    return summary


def calculate_composite(
    dimensions: Dict[str, DimensionScore],
    role: str = "general",
    job_id: Optional[str] = None,
) -> CompositeResult:
    """
    Calculate weighted composite score from 7 dimension scores.

    Steps:
      1. Get role-based weights
      2. Multiply each normalized score (0-1) by its weight
      3. Sum to get composite in 0-1 range
      4. Convert back to 1-5 scale
      5. Identify improvement priorities (dimensions scoring 1 or 2)
      6. Generate summary paragraph
    """
    job_id = job_id or "scoring"
    weights = get_weights(role)

    # Weighted sum (normalized scores are 0-1)
    weighted_sum = 0.0
    for dim_key, dim_score in dimensions.items():
        weight = weights.get(dim_key, 0.0)
        weighted_sum += dim_score.normalized * weight

    # Convert 0-1 back to 1-5 scale
    composite_score = 1.0 + (weighted_sum * 4.0)
    composite_score = round(max(1.0, min(5.0, composite_score)), 2)
    composite_pct = round((composite_score - 1.0) / 4.0 * 100, 1)

    # Improvement priorities: dimensions scoring <= 2.0
    priorities = [
        dim.name
        for dim in sorted(dimensions.values(), key=lambda d: d.raw_score)
        if dim.raw_score <= 2.0
    ]

    # Also add dimensions scoring 2.0-3.0 if no critical ones
    if not priorities:
        priorities = [
            dim.name
            for dim in sorted(dimensions.values(), key=lambda d: d.raw_score)[:2]
            if dim.raw_score < 4.0
        ]

    grade = _score_to_grade(composite_score)
    summary = _generate_summary(composite_score, dimensions, role)

    logger.info(
        f"[{job_id}] Composite: {composite_score}/5 ({composite_pct}%) "
        f"Grade: {grade} | Role: {role}"
    )

    return CompositeResult(
        composite_score=composite_score,
        composite_pct=composite_pct,
        role=role,
        dimensions=dimensions,
        improvement_priorities=priorities,
        summary=summary,
        grade=grade,
    )