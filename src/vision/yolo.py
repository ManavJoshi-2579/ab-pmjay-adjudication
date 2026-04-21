"""YOLOv8 detector facade."""

from __future__ import annotations

from src.core.state_manager import OCRPageResult, VisualDetection


class YOLODetector:
    """Heuristic-backed YOLO wrapper for production scaffolding."""

    def detect(self, ocr_result: OCRPageResult) -> list[VisualDetection]:
        """Detect signatures, stamps, QR codes, and implant stickers."""
        text = ocr_result.full_text.lower()
        detections: list[VisualDetection] = []
        if "signature" in text or "signed" in text:
            detections.append(self._make_detection(ocr_result.page_number, "signature", 0.84))
        if "stamp" in text or "seal" in text:
            detections.append(self._make_detection(ocr_result.page_number, "stamp", 0.82))
        if "qr" in text or "scan code" in text:
            detections.append(self._make_detection(ocr_result.page_number, "qr_code", 0.8))
        if "implant" in text or "sticker" in text:
            detections.append(self._make_detection(ocr_result.page_number, "implant_sticker", 0.79))
        return detections

    @staticmethod
    def _make_detection(page_number: int, label: str, confidence: float) -> VisualDetection:
        return VisualDetection(
            page_number=page_number,
            label=label,
            confidence=confidence,
            bbox=(60, 60, 180, 160),
            source="yolo",
        )
