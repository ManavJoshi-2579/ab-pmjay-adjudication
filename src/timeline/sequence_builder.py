"""Timeline assembly."""

from __future__ import annotations

from datetime import datetime

from src.core.state_manager import FieldCandidate, OCRPageResult, TimelineEvent
from src.timeline.event_classifier import EventClassifier


class SequenceBuilder:
    """Build a chronological care timeline."""

    EVENT_PRIORITY = {
        "admission": 0,
        "investigation": 1,
        "procedure": 2,
        "monitoring": 3,
        "discharge": 4,
    }

    def __init__(self) -> None:
        self.event_classifier = EventClassifier()

    def build(self, ocr_result: OCRPageResult, date_candidates: list[FieldCandidate]) -> list[TimelineEvent]:
        """Create timeline events from extracted date candidates."""
        events = [
            TimelineEvent(
                event_type=self.event_classifier.classify(ocr_result, str(candidate.value)),
                date=str(candidate.value),
                page_number=ocr_result.page_number,
                confidence=candidate.confidence,
                evidence=ocr_result.full_text[:160],
                metadata={"source_field": candidate.field_name},
            )
            for candidate in date_candidates
        ]
        deduped: dict[tuple[str, str, int], TimelineEvent] = {}
        for event in events:
            key = (event.event_type, event.date, event.page_number)
            current = deduped.get(key)
            if current is None or event.confidence > current.confidence:
                deduped[key] = event
        return sorted(
            deduped.values(),
            key=lambda item: (
                datetime.fromisoformat(item.date),
                self.EVENT_PRIORITY.get(item.event_type, 99),
                item.page_number,
            ),
        )
