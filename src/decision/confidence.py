"""Confidence aggregation."""

from __future__ import annotations

from statistics import mean

from src.core.state_manager import ClassificationResult, FieldCandidate, RuleViolation, TimelineEvent, VisualDetection


class ConfidenceAggregator:
    """Aggregate subsystem confidences into a single claim score."""

    def compute(
        self,
        classifications: list[ClassificationResult],
        fields: dict[str, list[FieldCandidate]],
        timeline: list[TimelineEvent],
        detections: list[VisualDetection],
        violations: list[RuleViolation],
    ) -> float:
        """Compute a calibrated raw confidence score."""
        module_scores = self.module_scores(classifications, fields, timeline, detections)
        values = list(module_scores.values())
        base_score = mean(values) if values else 0.4
        penalty = sum(0.12 if item.severity == "high" else 0.06 for item in violations)
        return max(0.0, min(0.99, base_score - penalty))

    def module_scores(
        self,
        classifications: list[ClassificationResult],
        fields: dict[str, list[FieldCandidate]],
        timeline: list[TimelineEvent],
        detections: list[VisualDetection],
    ) -> dict[str, float]:
        """Normalize scores across modules."""
        field_values = [item.confidence for candidates in fields.values() for item in candidates]
        scores: dict[str, float] = {}
        if classifications:
            scores["classification"] = round(mean(item.confidence for item in classifications), 4)
        if field_values:
            scores["extraction"] = round(mean(field_values), 4)
        if timeline:
            scores["timeline"] = round(mean(item.confidence for item in timeline), 4)
        if detections:
            scores["vision"] = round(mean(item.confidence for item in detections), 4)
        return scores
