"""LayoutLM-style entity extractor."""

from __future__ import annotations

import re

from src.core.state_manager import FieldCandidate, OCRPageResult


class LayoutLMFieldExtractor:
    """Structured field extractor using text heuristics as a model fallback."""

    def extract(self, ocr_result: OCRPageResult) -> list[FieldCandidate]:
        """Extract high-value fields from OCR text."""
        text = ocr_result.full_text
        lowered = text.lower()
        candidates: list[FieldCandidate] = []

        name_match = re.search(
            r"patient name[:\s]+([A-Za-z ]{3,}?)(?=\s+(?:diagnosis|procedure|admission|date)\b|$)",
            text,
            re.IGNORECASE,
        )
        if name_match:
            candidates.append(
                self._candidate(
                    "patient_name",
                    self._clean_phrase(name_match.group(1).strip()),
                    ocr_result,
                    0.9,
                    metadata={"char_span": name_match.span(), "pattern": "patient_name"},
                )
            )

        diagnosis_match = re.search(
            r"diagnosis[:\s]+([A-Za-z ]{3,}?)(?=\s+(?:procedure|discharge|date|amount)\b|$)",
            text,
            re.IGNORECASE,
        )
        if diagnosis_match:
            candidates.append(
                self._candidate(
                    "diagnosis",
                    self._clean_phrase(diagnosis_match.group(1).strip()),
                    ocr_result,
                    0.88,
                    metadata={"char_span": diagnosis_match.span(), "pattern": "diagnosis"},
                )
            )

        procedure_match = re.search(
            r"procedure[:\s]+([A-Za-z ]{3,}?)(?=\s+(?:date|amount|signature|stamp)\b|$)",
            text,
            re.IGNORECASE,
        )
        if procedure_match:
            procedure_value = self._clean_phrase(procedure_match.group(1).strip())
            if procedure_value:
                candidates.append(
                    self._candidate(
                        "procedure",
                        procedure_value,
                        ocr_result,
                        0.88,
                        metadata={"char_span": procedure_match.span(), "pattern": "procedure"},
                    )
                )

        for date_match in re.finditer(r"\b(20\d{2}[-/]\d{2}[-/]\d{2})\b", lowered):
            candidates.append(
                self._candidate(
                    "dates",
                    date_match.group(1),
                    ocr_result,
                    0.85,
                    metadata={"char_span": date_match.span(), "pattern": "date"},
                )
            )

        amount_context = any(keyword in lowered for keyword in ("amount", "bill", "invoice", "total", "inr", "rs"))
        for amount_match in re.finditer(r"\b(?:rs\.?|inr)?\s?(\d{3,7})\b", lowered):
            amount = int(amount_match.group(1))
            if amount_context and amount >= 10000 and amount <= 500000:
                candidates.append(
                    self._candidate(
                        "amounts",
                        amount,
                        ocr_result,
                        0.8,
                        metadata={"char_span": amount_match.span(), "pattern": "amount"},
                    )
                )

        return candidates

    @staticmethod
    def _candidate(
        field_name: str,
        value: object,
        ocr_result: OCRPageResult,
        confidence: float,
        metadata: dict | None = None,
    ) -> FieldCandidate:
        return FieldCandidate(
            field_name=field_name,
            value=value,
            confidence=confidence,
            page_number=ocr_result.page_number,
            bbox=(20, 20, 260, 42),
            source="layoutlm_extractor",
            metadata=metadata or {},
        )

    @staticmethod
    def _clean_phrase(value: str) -> str:
        """Trim common trailing document terms from extracted phrases."""
        cleaned = re.sub(
            r"\b(discharge|date|signature|stamp|surgeon|note|bill|invoice|total amount|amount)\b.*$",
            "",
            value,
            flags=re.IGNORECASE,
        ).strip()
        cleaned = re.sub(r"\bfinal\b$", "", cleaned, flags=re.IGNORECASE).strip()
        return re.sub(r"\s{2,}", " ", cleaned)
