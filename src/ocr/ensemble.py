"""OCR ensembling."""

from __future__ import annotations

from pathlib import Path

from src.core.state_manager import OCRPageResult, OCRWord
from src.ocr.doctr import DocTROCRProcessor
from src.ocr.paddle import PaddleOCRProcessor
from src.ocr.tesseract import TesseractOCRProcessor
from src.utils.io import compute_cache_key, load_json, save_json


class OCREnsemble:
    """Merge OCR outputs using confidence-weighted selection."""

    def __init__(
        self,
        cache_dir: str | None = None,
        weights: dict[str, float] | None = None,
        agreement_boost: float = 0.08,
        disagreement_penalty: float = 0.08,
    ) -> None:
        self.primary = PaddleOCRProcessor()
        self.fallbacks = [DocTROCRProcessor(), TesseractOCRProcessor()]
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.weights = weights or {"paddle": 1.0, "doctr": 0.85, "tesseract": 0.75}
        self.agreement_boost = agreement_boost
        self.disagreement_penalty = disagreement_penalty
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def extract(self, page_number: int, image_path: str, hint_text: str = "") -> OCRPageResult:
        """Run all OCR processors and return the strongest merged result."""
        cached = self._load_from_cache(page_number, image_path, hint_text)
        if cached is not None:
            return cached
        candidates = [self.primary.extract(page_number, image_path, hint_text)]
        candidates.extend(model.extract(page_number, image_path, hint_text) for model in self.fallbacks)
        ranked = sorted(
            candidates,
            key=lambda item: item.confidence * self.weights.get(item.source, 0.5),
            reverse=True,
        )
        best = ranked[0]
        merged_words = self._merge_words(candidates)
        adaptive_confidence, agreement = self._adaptive_confidence(candidates)
        result = OCRPageResult(
            page_number=page_number,
            full_text=best.full_text,
            words=merged_words,
            confidence=adaptive_confidence,
            source="ensemble",
            image_path=image_path,
            metadata={
                "cached": False,
                "selected_source": best.source,
                "agreement_ratio": agreement,
                "candidates": [
                    {"source": item.source, "confidence": item.confidence, "text_preview": item.full_text[:120]}
                    for item in ranked
                ],
            },
        )
        self._save_to_cache(result, hint_text)
        return result

    def extract_batch(self, pages: list[tuple[int, str, str]]) -> list[OCRPageResult]:
        """Extract OCR results for a batch of pages."""
        return [self.extract(page_number, image_path, hint_text) for page_number, image_path, hint_text in pages]

    @staticmethod
    def _merge_words(candidates: list[OCRPageResult]) -> list[OCRWord]:
        best_tokens: dict[str, OCRWord] = {}
        for candidate in candidates:
            for word in candidate.words:
                current = best_tokens.get(word.text.lower())
                if current is None or word.confidence > current.confidence:
                    best_tokens[word.text.lower()] = word
        return list(best_tokens.values())

    def _cache_path(self, page_number: int, image_path: str, hint_text: str) -> Path | None:
        """Return cache path for a page."""
        if self.cache_dir is None:
            return None
        key = compute_cache_key(page_number, image_path, hint_text)
        return self.cache_dir / f"{key}.json"

    def _load_from_cache(self, page_number: int, image_path: str, hint_text: str) -> OCRPageResult | None:
        """Load OCR result from cache when available."""
        cache_path = self._cache_path(page_number, image_path, hint_text)
        if cache_path is None or not cache_path.exists():
            return None
        payload = load_json(cache_path)
        words = [
            OCRWord(
                text=item["text"],
                confidence=item["confidence"],
                bbox=tuple(item["bbox"]),
                source=item["source"],
            )
            for item in payload.get("words", [])
        ]
        return OCRPageResult(
            page_number=payload["page_number"],
            full_text=payload["full_text"],
            words=words,
            confidence=payload["confidence"],
            source=payload["source"],
            image_path=payload["image_path"],
            metadata={**payload.get("metadata", {}), "cached": True},
        )

    def _save_to_cache(self, result: OCRPageResult, hint_text: str) -> None:
        """Persist OCR result for reuse."""
        cache_path = self._cache_path(result.page_number, result.image_path, hint_text)
        if cache_path is None:
            return
        save_json(
            cache_path,
            {
                "page_number": result.page_number,
                "full_text": result.full_text,
                "words": [
                    {
                        "text": item.text,
                        "confidence": item.confidence,
                        "bbox": item.bbox,
                        "source": item.source,
                    }
                    for item in result.words
                ],
                "confidence": result.confidence,
                "source": result.source,
                "image_path": result.image_path,
                "metadata": result.metadata,
            },
        )

    def _adaptive_confidence(self, candidates: list[OCRPageResult]) -> tuple[float, float]:
        """Compute confidence from agreement and disagreement."""
        weighted = sum(item.confidence * self.weights.get(item.source, 0.5) for item in candidates) / len(candidates)
        texts = [self._normalize_for_agreement(item.full_text) for item in candidates if item.full_text.strip()]
        unique_texts = set(texts)
        agreement_ratio = 1.0 if len(unique_texts) == 1 and texts else 1.0 / max(len(unique_texts), 1)
        adjusted = weighted
        if agreement_ratio >= 0.75:
            adjusted += self.agreement_boost * agreement_ratio
        else:
            adjusted -= self.disagreement_penalty * (1 - agreement_ratio)
        return max(0.0, min(0.99, adjusted)), round(agreement_ratio, 4)

    @staticmethod
    def _normalize_for_agreement(text: str) -> str:
        """Normalize OCR text before comparing engine agreement."""
        return " ".join(text.lower().replace("|", " ").split())
