"""CNN-style image classifier fallback."""

from __future__ import annotations

from src.core.state_manager import ClassificationResult, OCRPageResult


class CNNFallbackClassifier:
    """Lightweight fallback classifier based on OCR cues."""

    def predict(self, ocr_result: OCRPageResult) -> ClassificationResult:
        """Generate a secondary class prediction."""
        text = ocr_result.full_text.lower()
        if "signature" in text and "bill" in text:
            label, confidence = "bill", 0.72
        elif "patient name" in text:
            label, confidence = "claim_form", 0.7
        else:
            label, confidence = "other", 0.45
        return ClassificationResult(
            page_number=ocr_result.page_number,
            label=label,
            confidence=confidence,
            evidence=[f"cnn:{label}"],
            metadata={"model": "cnn"},
        )
