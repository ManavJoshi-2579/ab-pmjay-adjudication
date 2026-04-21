"""Confidence calibration."""

from __future__ import annotations

from statistics import mean


class ConfidenceCalibrator:
    """Smooth raw scores into conservative production values."""

    def calibrate(
        self,
        raw_score: float,
        module_scores: dict[str, float] | None = None,
        agreement: float = 1.0,
        inconsistency_penalty: float = 0.08,
        agreement_boost: float = 0.06,
        missing_field_penalty: float = 0.08,
        missing_field_ratio: float = 0.0,
        rule_alignment_boost: float = 0.08,
        rule_alignment: float = 1.0,
    ) -> float:
        """Normalize module scores, penalize inconsistency, and reward agreement."""
        normalized = raw_score
        if module_scores:
            mean_score = mean(module_scores.values()) if module_scores else raw_score
            spread = max(module_scores.values()) - min(module_scores.values()) if module_scores else 0.0
            normalized = (raw_score + mean_score) / 2
            normalized -= spread * inconsistency_penalty
        normalized -= missing_field_ratio * missing_field_penalty
        normalized += max(0.0, rule_alignment - 0.5) * rule_alignment_boost
        normalized += max(0.0, agreement - 0.5) * agreement_boost
        return round(max(0.0, min(0.99, 0.05 + normalized * 0.92)), 4)
