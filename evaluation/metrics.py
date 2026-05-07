"""Evaluation metrics."""

from __future__ import annotations


def precision(tp: int, fp: int) -> float:
    """Compute precision."""
    return tp / (tp + fp) if tp + fp else 0.0


def recall(tp: int, fn: int) -> float:
    """Compute recall."""
    return tp / (tp + fn) if tp + fn else 0.0


def f1_score(tp: int, fp: int, fn: int) -> float:
    """Compute F1 score."""
    p = precision(tp, fp)
    r = recall(tp, fn)
    return 2 * p * r / (p + r) if p + r else 0.0
