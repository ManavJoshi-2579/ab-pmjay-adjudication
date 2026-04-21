"""Table parser for billing-like documents."""

from __future__ import annotations

import re

from src.core.state_manager import FieldCandidate, OCRPageResult


class TableParser:
    """Extract amount-like values from tabular bill pages."""

    def extract(self, ocr_result: OCRPageResult) -> list[FieldCandidate]:
        """Pull structured totals from bill text."""
        text = ocr_result.full_text.lower()
        normalized = text.translate(str.maketrans({"|": " ", "o": "0", "l": "1", "i": "1"}))
        candidates: list[FieldCandidate] = []
        if not any(token in text for token in ("bill", "amount", "invoice", "total", "payable")):
            return candidates
        for match in re.finditer(r"\b(\d{3,8})\b", normalized):
            value = int(match.group(1))
            window = normalized[max(0, match.start() - 24) : match.end() + 24]
            if 1000 <= value <= 5000000 and any(token in window for token in ("bill", "amount", "total", "payable", "invoice", "rs", "inr")):
                candidates.append(
                    FieldCandidate(
                        field_name="amounts",
                        value=value,
                        confidence=0.82 if value >= 10000 else 0.72,
                        page_number=ocr_result.page_number,
                        bbox=(30, 30, 180, 55),
                        source="table_parser",
                        metadata={"char_span": match.span(), "table_context": window.strip()},
                    )
                )
        return candidates
