"""Vision postprocessing."""

from __future__ import annotations

from src.core.state_manager import VisualDetection


class VisionPostProcessor:
    """Filter and deduplicate visual detections."""

    def process(self, detections: list[VisualDetection]) -> list[VisualDetection]:
        """Keep the highest-confidence detection per label and page."""
        best: dict[tuple[int, str], VisualDetection] = {}
        for detection in detections:
            key = (detection.page_number, detection.label)
            current = best.get(key)
            if current is None or detection.confidence > current.confidence:
                best[key] = detection
        return list(best.values())
