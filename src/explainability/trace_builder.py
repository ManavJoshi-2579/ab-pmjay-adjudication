"""Decision trace construction."""

from __future__ import annotations

from src.core.state_manager import ClassificationResult, FieldCandidate, RuleViolation, TimelineEvent, VisualDetection


class TraceBuilder:
    """Build an interpretable claim trace."""

    def build(
        self,
        classifications: list[ClassificationResult],
        fields: dict[str, list[FieldCandidate]],
        detections: list[VisualDetection],
        timeline: list[TimelineEvent],
        violations: list[RuleViolation],
    ) -> dict:
        """Create a compact trace artifact."""
        return {
            "classifications": [
                {
                    "page_number": item.page_number,
                    "label": item.label,
                    "confidence": item.confidence,
                    "evidence": item.evidence,
                    "metadata": item.metadata,
                }
                for item in classifications
            ],
            "fields": {
                field_name: [
                    {
                        "value": item.value,
                        "page_number": item.page_number,
                        "bbox": item.bbox,
                        "confidence": item.confidence,
                        "source": item.source,
                        "metadata": item.metadata,
                    }
                    for item in candidates
                ]
                for field_name, candidates in fields.items()
            },
            "visual_detections": [
                {
                    "label": item.label,
                    "page_number": item.page_number,
                    "bbox": item.bbox,
                    "confidence": item.confidence,
                    "source": item.source,
                }
                for item in detections
            ],
            "timeline": [
                {
                    "event_type": item.event_type,
                    "date": item.date,
                    "page_number": item.page_number,
                    "confidence": item.confidence,
                    "metadata": item.metadata,
                }
                for item in timeline
            ],
            "violations": [
                {
                    "rule_name": item.rule_name,
                    "severity": item.severity,
                    "message": item.message,
                    "evidence": item.evidence,
                }
                for item in violations
            ],
        }
