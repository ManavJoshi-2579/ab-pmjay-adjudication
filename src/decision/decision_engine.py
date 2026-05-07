"""Final adjudication engine."""

from __future__ import annotations

from src.core.state_manager import DecisionResult, RuleViolation
from src.decision.calibrator import ConfidenceCalibrator
from src.decision.confidence import ConfidenceAggregator


class DecisionEngine:
    """Convert signals and violations into a final claim decision."""

    def __init__(self, thresholds: dict) -> None:
        self.thresholds = thresholds
        self.aggregator = ConfidenceAggregator()
        self.calibrator = ConfidenceCalibrator()

    def decide(
        self,
        classifications,
        fields,
        timeline,
        detections,
        violations: list[RuleViolation],
        evidence: list[dict],
    ) -> DecisionResult:
        """Produce pass, conditional, or fail."""
        raw_score = self.aggregator.compute(classifications, fields, timeline, detections, violations)
        module_scores = self.aggregator.module_scores(classifications, fields, timeline, detections)
        agreement = self._agreement_signal(classifications, violations)
        field_coverage = self._field_coverage(fields)
        missing_field_ratio = 1.0 - field_coverage
        rule_alignment = self._rule_alignment(violations)
        confidence = self.calibrator.calibrate(
            raw_score,
            module_scores=module_scores,
            agreement=agreement,
            inconsistency_penalty=self.thresholds.get("decision", {}).get("inconsistency_penalty", 0.08),
            agreement_boost=self.thresholds.get("decision", {}).get("agreement_boost", 0.06),
            missing_field_penalty=self.thresholds.get("decision", {}).get("missing_field_penalty", 0.08),
            missing_field_ratio=missing_field_ratio,
            rule_alignment_boost=self.thresholds.get("decision", {}).get("rule_alignment_boost", 0.08),
            rule_alignment=rule_alignment,
        )
        if self._final_agreement(classifications, timeline, violations):
            confidence = min(0.99, confidence + self.thresholds.get("decision", {}).get("final_agreement_boost", 0.06))
        high_violations = [item for item in violations if item.severity == "high"]
        medium_violations = [item for item in violations if item.severity == "medium"]
        safe_mode = self._safe_mode(classifications, confidence)
        if high_violations:
            status = "Fail"
        elif safe_mode:
            status = "Conditional"
        elif medium_violations or confidence < self.thresholds.get("decision", {}).get("pass_score", 0.85) or field_coverage < 0.6:
            status = "Conditional"
        else:
            status = "Pass"
        reasons = [item.message for item in violations] or ["All configured checks passed."]
        if field_coverage < 0.6:
            reasons.append("Structured field coverage below preferred threshold.")
        if safe_mode:
            reasons.append("Safe-mode applied: low classification confidence increased reliance on rule validation.")
        return DecisionResult(status=status, confidence=confidence, reasons=reasons, evidence=evidence)

    @staticmethod
    def _field_coverage(fields: dict) -> float:
        """Return fraction of core fields recovered."""
        core_fields = ("patient_name", "diagnosis", "procedure", "dates", "amounts")
        present = sum(1 for field_name in core_fields if fields.get(field_name))
        return present / len(core_fields)

    @staticmethod
    def _agreement_signal(classifications, violations: list[RuleViolation]) -> float:
        """Estimate cross-module agreement from classification consensus and rule cleanliness."""
        if not classifications:
            return 0.0
        agreement_values = [float(item.metadata.get("agreement_ratio", 1.0)) for item in classifications]
        base = sum(agreement_values) / len(agreement_values)
        penalty = min(0.4, len(violations) * 0.05)
        return max(0.0, min(1.0, base - penalty))

    @staticmethod
    def _rule_alignment(violations: list[RuleViolation]) -> float:
        """Estimate how aligned the claim is with rules."""
        if not violations:
            return 1.0
        penalty = sum(0.2 if item.severity == "high" else 0.1 if item.severity == "medium" else 0.04 for item in violations)
        return max(0.0, min(1.0, 1.0 - penalty))

    def _safe_mode(self, classifications, confidence: float) -> bool:
        """Switch to safe-mode when page-level classification remains uncertain."""
        if not classifications:
            return True
        mean_classification = sum(item.confidence for item in classifications) / len(classifications)
        threshold = self.thresholds.get("decision", {}).get("safe_mode_threshold", 0.72)
        return mean_classification < threshold or confidence < threshold

    @staticmethod
    def _final_agreement(classifications, timeline, violations: list[RuleViolation]) -> bool:
        """Return true when classification, rules, and timeline all align strongly."""
        if violations:
            return False
        if not classifications or not timeline:
            return False
        mean_classification = sum(item.confidence for item in classifications) / len(classifications)
        mean_timeline = sum(item.confidence for item in timeline) / len(timeline)
        return mean_classification >= 0.85 and mean_timeline >= 0.8
