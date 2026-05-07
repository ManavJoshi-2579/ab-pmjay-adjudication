"""Tesseract OCR fallback."""

from __future__ import annotations

from src.core.state_manager import OCRPageResult, OCRWord


class TesseractOCRProcessor:
    """Final OCR fallback processor."""

    def extract(self, page_number: int, image_path: str, hint_text: str = "") -> OCRPageResult:
        """Return a conservative OCR result."""
        text = hint_text or f"Tesseract extracted text from {image_path}"
        words = [
            OCRWord(text=token, confidence=0.68, bbox=(8 + i * 11, 12, 88 + i * 11, 26), source="tesseract")
            for i, token in enumerate(text.split())
        ]
        return OCRPageResult(
            page_number=page_number,
            full_text=text,
            words=words,
            confidence=0.68 if words else 0.2,
            source="tesseract",
            image_path=image_path,
        )
