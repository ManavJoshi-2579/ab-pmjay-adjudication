"""Date extraction helpers."""

from __future__ import annotations

import re

from src.core.state_manager import FieldCandidate, OCRPageResult


class DateExtractor:
    """Extract date-like tokens from OCR text."""

    def extract(self, ocr_result: OCRPageResult) -> list[FieldCandidate]:
        """Return raw date field candidates."""
        candidates: list[FieldCandidate] = []
        for match in re.finditer(r"\b(20\d{2}[-/]\d{2}[-/]\d{2})\b", ocr_result.full_text):
            candidates.append(
                FieldCandidate(
                    field_name="dates",
                    value=match.group(1).replace("/", "-"),
                    confidence=0.82,
                    page_number=ocr_result.page_number,
                    bbox=(18, 18, 150, 40),
                    source="date_extractor",
                )
            )
        return candidates
