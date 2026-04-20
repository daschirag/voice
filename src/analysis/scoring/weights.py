"""
Role-Based Weight Matrix
------------------------
Different professional roles demand different communication skills.
Weights must sum to 1.0 per role.

Roles:
  general    : equal weights (baseline)
  sales      : delivery + pauses + tone weighted higher
  executive  : language quality + clarity + punctuation weighted higher
  coaching   : all dimensions weighted for development feedback
  interview  : clarity + language + delivery weighted higher
"""
from typing import Dict
from src.core.logger import logger

# Weight matrices per role
# Keys must match the dimension keys in normalizer.py
ROLE_WEIGHTS: Dict[str, Dict[str, float]] = {
    "general": {
        "clarity":          0.143,
        "filler_words":     0.143,
        "pauses":           0.143,
        "punctuation":      0.143,
        "language_quality": 0.143,
        "delivery":         0.143,
        "tone":             0.142,   # slightly less to sum to 1.0
    },
    "sales": {
        "clarity":          0.10,
        "filler_words":     0.10,
        "pauses":           0.20,    # pauses project confidence in sales
        "punctuation":      0.05,
        "language_quality": 0.10,
        "delivery":         0.25,    # pace control is critical in sales
        "tone":             0.20,    # warmth and energy close deals
    },
    "executive": {
        "clarity":          0.20,    # executive presence requires precision
        "filler_words":     0.20,    # fillers destroy credibility at senior level
        "pauses":           0.10,
        "punctuation":      0.15,    # structured delivery signals authority
        "language_quality": 0.25,    # vocabulary richness signals intelligence
        "delivery":         0.05,
        "tone":             0.05,
    },
    "interview": {
        "clarity":          0.20,
        "filler_words":     0.15,
        "pauses":           0.10,
        "punctuation":      0.10,
        "language_quality": 0.20,
        "delivery":         0.15,
        "tone":             0.10,
    },
    "coaching": {
        "clarity":          0.15,
        "filler_words":     0.15,
        "pauses":           0.15,
        "punctuation":      0.15,
        "language_quality": 0.15,
        "delivery":         0.15,
        "tone":             0.10,
    },
}

# Default role if not specified
DEFAULT_ROLE = "general"


def get_weights(role: str) -> Dict[str, float]:
    """
    Get weight matrix for a given role.
    Falls back to 'general' if role not found.
    """
    role = role.lower().strip()
    if role not in ROLE_WEIGHTS:
        logger.warning(f"Unknown role '{role}' - using 'general' weights")
        role = DEFAULT_ROLE

    weights = ROLE_WEIGHTS[role]

    # Validate weights sum to ~1.0
    total = sum(weights.values())
    if abs(total - 1.0) > 0.01:
        logger.warning(f"Weights for role '{role}' sum to {total:.3f}, not 1.0")

    return weights


def get_available_roles() -> list:
    """Return list of all available role names."""
    return list(ROLE_WEIGHTS.keys())