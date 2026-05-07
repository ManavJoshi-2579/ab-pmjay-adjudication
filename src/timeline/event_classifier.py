"""Temporal event classification."""

from __future__ import annotations

from src.core.state_manager import OCRPageResult


class EventClassifier:
    """Classify dates into clinical events."""

    def classify(self, ocr_result: OCRPageResult, date_value: str) -> str:
        """Infer an event type from local page context."""
        text = ocr_result.full_text.lower()
        if "discharge date" in text or "date of discharge" in text:
            return "discharge"
        if "admission date" in text or "date of admission" in text:
            return "admission"
        if "admission" in text:
            return "admission"
        if "discharge" in text:
            return "discharge"
        if "procedure" in text or "surgery" in text or "operation" in text:
            return "procedure"
        if "investigation" in text or "lab" in text:
            return "investigation"
        return "monitoring"
