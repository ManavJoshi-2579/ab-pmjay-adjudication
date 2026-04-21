"""Keyword-based document validation."""

from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher

from src.core.state_manager import ClassificationResult, OCRPageResult


class KeywordRuleClassifier:
    """Cheap but highly interpretable keyword classifier."""

    KEYWORDS = {
        "claim_form": ["claim form", "patient name", "admission date"],
        "discharge_summary": ["discharge summary", "diagnosis", "discharge"],
        "procedure_note": ["procedure", "surgery", "operation"],
        "bill": ["bill", "amount", "invoice", "total"],
    }

    def __init__(
        self,
        keyword_boosts: dict[str, list[str]] | None = None,
        hard_overrides: dict[str, list[str]] | None = None,
    ) -> None:
        self.keyword_boosts = keyword_boosts or {}
        self.hard_overrides = hard_overrides or {}

    def predict(self, ocr_result: OCRPageResult) -> ClassificationResult:
        """Classify a page using weighted keyword overlap."""
        text = ocr_result.full_text.lower()
        for label, phrases in self.hard_overrides.items():
            if any(self._contains_fuzzy(text, phrase) for phrase in phrases):
                return ClassificationResult(
                    page_number=ocr_result.page_number,
                    label=label,
                    confidence=0.92,
                    evidence=[f"hard_override:{label}"],
                    metadata={"model": "keyword_rules", "score_hits": len(phrases), "hard_override": True},
                )
        scores = Counter()
        for label, keywords in self.KEYWORDS.items():
            scores[label] = sum(1 for keyword in keywords if self._contains_fuzzy(text, keyword))
            scores[label] += sum(1 for keyword in self.keyword_boosts.get(label, []) if self._contains_fuzzy(text, keyword))
        if not scores:
            label, confidence = "other", 0.3
        else:
            label, raw = scores.most_common(1)[0]
            confidence = min(0.5 + raw * 0.15, 0.89) if raw else 0.3
            if raw == 0:
                label = "other"
        return ClassificationResult(
            page_number=ocr_result.page_number,
            label=label,
            confidence=confidence,
            evidence=[f"keywords:{label}"],
            metadata={"model": "keyword_rules", "score_hits": raw if 'raw' in locals() else 0},
        )

    @staticmethod
    def _contains_fuzzy(text: str, phrase: str, threshold: float = 0.82) -> bool:
        """Return true when a phrase appears directly or approximately."""
        if phrase in text:
            return True
        tokens = text.split()
        phrase_tokens = phrase.split()
        window = len(phrase_tokens)
        if window == 0 or len(tokens) < window:
            return False
        for index in range(len(tokens) - window + 1):
            candidate = " ".join(tokens[index : index + window])
            if SequenceMatcher(None, candidate, phrase).ratio() >= threshold:
                return True
        return False
