"""Evaluation validators."""

from __future__ import annotations


def validate_target(score_summary: dict[str, float], threshold: float = 0.95) -> bool:
    """Check if overall score meets the target."""
    return score_summary.get("overall", 0.0) >= threshold
