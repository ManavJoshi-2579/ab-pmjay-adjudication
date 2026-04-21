"""Regex-based extraction fallback."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from src.core.state_manager import FieldCandidate, OCRPageResult


class RegexBackupExtractor:
    """Simple resilient extractor for low-resource environments."""

    def extract(self, ocr_result: OCRPageResult) -> list[FieldCandidate]:
        """Extract fields through broad regex patterns."""
        text = ocr_result.full_text
        normalized = self._normalize(text)
        candidates: list[FieldCandidate] = []
        name_match = re.search(
            r"(?:patient[\s:|._-]*name|beneficiary[\s:|._-]*name)[:\s-]+([a-z ]{3,50}?)(?=\s+(?:diagnosis|procedure|date|amount)\b|$)",
            normalized,
            re.IGNORECASE,
        )
        if name_match:
            candidates.append(
                FieldCandidate(
                    field_name="patient_name",
                    value=" ".join(part.capitalize() for part in name_match.group(1).split()[:4]),
                    confidence=0.74,
                    page_number=ocr_result.page_number,
                    bbox=(25, 24, 250, 48),
                    source="regex_backup",
                    metadata={"char_span": name_match.span(), "pattern": "patient_name"},
                )
            )
        patterns = {
            "diagnosis": ("appendicitis", "fracture", "cataract"),
            "procedure": ("appendectomy", "appendicectomy", "orif", "phaco", "implant"),
        }
        for field_name, terms in patterns.items():
            match = self._best_fuzzy_term(normalized, terms)
            if match is not None:
                value, score = match
                candidates.append(
                    FieldCandidate(
                        field_name=field_name,
                        value=value,
                        confidence=0.65 + min(0.12, max(0.0, score - 0.82)),
                        page_number=ocr_result.page_number,
                        bbox=(25, 24, 250, 48),
                        source="regex_backup",
                        metadata={"fuzzy_score": round(score, 3), "recovered": True},
                    )
                )
        return candidates

    @staticmethod
    def _normalize(text: str) -> str:
        normalized = text.lower()
        normalized = normalized.translate(str.maketrans({"|": " ", "@": "a", "$": "s"}))
        normalized = re.sub(r"(?<=[a-z])0(?=[a-z])", "o", normalized)
        normalized = re.sub(r"(?<=[a-z])1(?=[a-z])", "l", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    @staticmethod
    def _best_fuzzy_term(text: str, terms: tuple[str, ...]) -> tuple[str, float] | None:
        words = text.split()
        best: tuple[str, float] | None = None
        for term in terms:
            token_count = len(term.split())
            for index in range(0, max(1, len(words) - token_count + 1)):
                chunk = " ".join(words[index : index + token_count])
                score = SequenceMatcher(None, chunk, term).ratio()
                if score >= 0.82 and (best is None or score > best[1]):
                    best = (term, score)
        return best
