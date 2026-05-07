"""Fallback routing logic."""

from __future__ import annotations

from src.core.state_manager import ClassificationResult, FieldCandidate


class FallbackLogic:
    """Determine when to activate fallback behavior."""

    def should_fallback_classification(self, classification: ClassificationResult, threshold: float) -> bool:
        """Return true when classifier confidence is too low."""
        agreement_ratio = float(classification.metadata.get("agreement_ratio", 1.0))
        return classification.confidence < threshold or agreement_ratio < 0.67

    def should_retry_ocr(self, ocr_confidence: float, threshold: float) -> bool:
        """Return true when OCR should be retried with stronger preprocessing."""
        return ocr_confidence < threshold

    def extraction_incomplete(self, fields: dict[str, list[FieldCandidate]], completeness_threshold: float) -> bool:
        """Return true when core extraction coverage is insufficient."""
        core_fields = ("patient_name", "diagnosis", "procedure", "dates", "amounts")
        coverage = sum(1 for field_name in core_fields if fields.get(field_name)) / len(core_fields)
        return coverage < completeness_threshold
