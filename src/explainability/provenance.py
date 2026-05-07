"""Evidence builders."""

from __future__ import annotations

from src.core.state_manager import FieldCandidate, VisualDetection


class ProvenanceBuilder:
    """Convert model outputs into portable evidence records."""

    def from_field(self, item: FieldCandidate, source_document: str) -> dict:
        """Build evidence for a structured field."""
        return {
            "type": "field",
            "field": item.field_name,
            "value": item.value,
            "page_number": item.page_number,
            "bbox": item.bbox,
            "source_document": source_document,
            "source": item.source,
            "confidence": item.confidence,
            "metadata": item.metadata,
        }

    def from_detection(self, item: VisualDetection, source_document: str) -> dict:
        """Build evidence for a visual detection."""
        return {
            "type": "visual",
            "label": item.label,
            "page_number": item.page_number,
            "bbox": item.bbox,
            "source_document": source_document,
            "source": item.source,
            "confidence": item.confidence,
        }
