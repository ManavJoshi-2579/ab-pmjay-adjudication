"""Detection validators."""

from __future__ import annotations

from src.core.state_manager import VisualDetection


class VisionValidator:
    """Validate detections against confidence thresholds."""

    def __init__(self, min_confidence: float = 0.55) -> None:
        self.min_confidence = min_confidence

    def validate(self, detections: list[VisualDetection]) -> list[VisualDetection]:
        """Return only reliable detections."""
        return [detection for detection in detections if detection.confidence >= self.min_confidence]
