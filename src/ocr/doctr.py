"""Secondary OCR fallback."""

from __future__ import annotations

from src.core.state_manager import OCRPageResult, OCRWord


class DocTROCRProcessor:
    """Lightweight DocTR facade."""

    def extract(self, page_number: int, image_path: str, hint_text: str = "") -> OCRPageResult:
        """Return fallback OCR output with slightly lower confidence."""
        text = hint_text or f"DocTR extracted text from {image_path}"
        words = [
            OCRWord(text=token, confidence=0.74, bbox=(12 + i * 10, 14, 92 + i * 10, 30), source="doctr")
            for i, token in enumerate(text.split())
        ]
        return OCRPageResult(
            page_number=page_number,
            full_text=text,
            words=words,
            confidence=0.74 if words else 0.2,
            source="doctr",
            image_path=image_path,
        )
