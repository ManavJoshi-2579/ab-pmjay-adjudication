"""OCR retry policies."""

from __future__ import annotations

from src.core.state_manager import OCRPageResult
from src.ocr.doctr import DocTROCRProcessor
from src.ocr.tesseract import TesseractOCRProcessor
from src.utils.io import preprocess_image


class OCRRetryHandler:
    """Retry low-confidence OCR using secondary engines."""

    def __init__(self) -> None:
        self.retry_models = [DocTROCRProcessor(), TesseractOCRProcessor()]

    def recover(
        self,
        ocr_result: OCRPageResult,
        threshold: float,
        retry_profile: str = "aggressive",
        preprocess_dir: str | None = None,
    ) -> OCRPageResult:
        """Retry OCR if confidence is too low."""
        if ocr_result.confidence >= threshold:
            return ocr_result
        best = ocr_result
        retry_image_path = ocr_result.image_path
        if preprocess_dir:
            retry_image_path = str(preprocess_image(ocr_result.image_path, preprocess_dir, profile=retry_profile))
        for model in self.retry_models:
            candidate = model.extract(ocr_result.page_number, retry_image_path, ocr_result.full_text)
            if candidate.confidence > best.confidence:
                best = candidate
        best.metadata["recovered_from"] = ocr_result.source
        best.metadata["recovery_trigger_threshold"] = threshold
        best.metadata["retry_profile"] = retry_profile
        return best
