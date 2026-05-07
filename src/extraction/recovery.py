"""Robust extraction recovery and confidence reconciliation."""

from __future__ import annotations

import re
from dataclasses import replace
from difflib import SequenceMatcher

from src.core.state_manager import FieldCandidate, OCRPageResult


class ExtractionRecovery:
    """Recover fragmented fields and rescore candidates under noisy OCR."""

    def __init__(self, config: dict | None = None, thresholds: dict | None = None) -> None:
        self.config = config or {}
        self.thresholds = thresholds or {}
        self.fuzzy_threshold = float(self.thresholds.get("fuzzy_match_threshold", 0.82))
        self.min_confidence = float(self.thresholds.get("min_field_confidence", 0.6))
        self.conflict_penalty = float(self.thresholds.get("conflict_penalty", 0.08))
        self.support_bonus = float(self.thresholds.get("support_bonus", 0.05))
        self.inference_penalty = float(self.thresholds.get("inference_penalty", 0.12))
        self.section_penalty = float(self.thresholds.get("section_penalty", 0.06))
        self.field_aliases = self.config.get(
            "field_aliases",
            {
                "patient_name": ["patient name", "patient", "beneficiary name", "name of patient"],
                "diagnosis": ["diagnosis", "final diagnosis", "provisional diagnosis"],
                "procedure": ["procedure", "procedure done", "operation", "operation performed"],
                "amounts": ["amount", "bill amount", "total amount", "invoice", "net payable", "total"],
                "dates": ["date", "admission date", "discharge date", "procedure date"],
            },
        )
        self.field_vocab = self.config.get(
            "field_vocab",
            {
                "diagnosis": ["appendicitis", "fracture", "cataract"],
                "procedure": ["appendectomy", "appendicectomy", "orif", "phaco", "implant", "implantation"],
            },
        )
        self.section_aliases = self.config.get(
            "section_aliases",
            {
                "claim_form": ["claim form", "preauth", "claim id"],
                "discharge_summary": ["discharge summary", "date of discharge", "final diagnosis"],
                "procedure_note": ["procedure note", "operation note", "operation theatre", "surgeon"],
                "bill": ["final bill", "invoice", "total amount", "bill amount"],
            },
        )

    def recover(self, ocr_result: OCRPageResult, candidates: list[FieldCandidate]) -> list[FieldCandidate]:
        """Return candidates with recovery heuristics and confidence reconciliation."""
        text = ocr_result.full_text or ""
        normalized_text = self._normalize_text(text)
        sections = self._detect_sections(normalized_text)
        recovered = list(candidates)
        recovered.extend(self._recover_labeled_fields(ocr_result, normalized_text, sections))
        recovered.extend(self._recover_from_vocabulary(ocr_result, normalized_text, sections, recovered))
        recovered.extend(self._recover_amounts(ocr_result, normalized_text, sections))
        return self._reconcile(recovered, normalized_text, sections)

    def _recover_labeled_fields(
        self,
        ocr_result: OCRPageResult,
        normalized_text: str,
        sections: list[dict[str, object]],
    ) -> list[FieldCandidate]:
        stop_markers = sorted(
            {alias for aliases in self.field_aliases.values() for alias in aliases},
            key=len,
            reverse=True,
        )
        stop_pattern = "|".join(re.escape(item) for item in stop_markers)
        candidates: list[FieldCandidate] = []
        for field_name in ("patient_name", "diagnosis", "procedure"):
            for alias in self.field_aliases.get(field_name, []):
                pattern = rf"{self._alias_pattern(alias)}\s*[:\-]?\s*([a-z0-9,./() \n]{{3,80}}?)(?=(?:{stop_pattern})\b|$)"
                for match in re.finditer(pattern, normalized_text, re.IGNORECASE):
                    value = self._clean_value(field_name, match.group(1))
                    if not value:
                        continue
                    candidates.append(
                        self._candidate(
                            field_name,
                            value,
                            ocr_result,
                            confidence=0.78,
                            source="recovery_labeled",
                            section=self._section_for_position(match.start(), sections),
                            metadata={"char_span": match.span(), "recovered": True, "alias": alias},
                        )
                    )
        for match in re.finditer(r"\b(20\d{2}[-/]\d{2}[-/]\d{2})\b", normalized_text):
            candidates.append(
                self._candidate(
                    "dates",
                    match.group(1).replace("/", "-"),
                    ocr_result,
                    confidence=0.76,
                    source="recovery_dates",
                    section=self._section_for_position(match.start(), sections),
                    metadata={"char_span": match.span(), "recovered": True},
                )
            )
        return candidates

    def _recover_from_vocabulary(
        self,
        ocr_result: OCRPageResult,
        normalized_text: str,
        sections: list[dict[str, object]],
        existing: list[FieldCandidate],
    ) -> list[FieldCandidate]:
        present_fields = {item.field_name for item in existing}
        candidates: list[FieldCandidate] = []
        for field_name in ("diagnosis", "procedure"):
            if field_name in present_fields:
                continue
            for term in self.field_vocab.get(field_name, []):
                match = self._find_fuzzy_term(normalized_text, term)
                if match is None:
                    continue
                value, score, start = match
                candidates.append(
                    self._candidate(
                        field_name,
                        value,
                        ocr_result,
                        confidence=max(self.min_confidence, 0.8 - self.inference_penalty + (score - self.fuzzy_threshold) * 0.25),
                        source="recovery_vocab",
                        section=self._section_for_position(start, sections),
                        metadata={"recovered": True, "inferred": True, "vocab_term": term, "match_score": round(score, 3)},
                    )
                )
                break
        return candidates

    def _recover_amounts(
        self,
        ocr_result: OCRPageResult,
        normalized_text: str,
        sections: list[dict[str, object]],
    ) -> list[FieldCandidate]:
        candidates: list[FieldCandidate] = []
        amount_aliases = self.field_aliases.get("amounts", [])
        label_pattern = "|".join(self._alias_pattern(alias) for alias in amount_aliases)
        for match in re.finditer(
            rf"(?:{label_pattern})\s*[:\-]?\s*(?:rs\.?|inr)?\s*([0-9oOlLiI,]{{3,12}})",
            normalized_text,
            re.IGNORECASE,
        ):
            value = self._parse_amount(match.group(1))
            if value is None:
                continue
            candidates.append(
                self._candidate(
                    "amounts",
                    value,
                    ocr_result,
                    confidence=0.81,
                    source="recovery_amount",
                    section=self._section_for_position(match.start(), sections),
                    metadata={"char_span": match.span(), "recovered": True},
                )
            )
        return candidates

    def _reconcile(
        self,
        candidates: list[FieldCandidate],
        normalized_text: str,
        sections: list[dict[str, object]],
    ) -> list[FieldCandidate]:
        grouped: dict[str, list[FieldCandidate]] = {}
        for item in candidates:
            grouped.setdefault(item.field_name, []).append(item)

        reconciled: list[FieldCandidate] = []
        for field_name, items in grouped.items():
            value_counts: dict[str, int] = {}
            for item in items:
                normalized_value = self._normalize_value(item.value)
                value_counts[normalized_value] = value_counts.get(normalized_value, 0) + 1
            conflict_count = max(0, len(value_counts) - 1)
            for item in items:
                normalized_value = self._normalize_value(item.value)
                support = value_counts.get(normalized_value, 1)
                metadata = dict(item.metadata)
                metadata.setdefault("section", self._infer_section(metadata, sections))
                metadata["support_count"] = support
                metadata["conflict_count"] = conflict_count
                if self._value_appears_in_text(str(item.value), normalized_text):
                    metadata["text_supported"] = True
                confidence = item.confidence + max(0, support - 1) * self.support_bonus
                if conflict_count and support == 1:
                    confidence -= self.conflict_penalty * conflict_count
                if metadata.get("section") == "mixed":
                    confidence -= self.section_penalty
                confidence = max(0.0, min(0.99, confidence))
                reconciled.append(replace(item, confidence=confidence, metadata=metadata))
        return reconciled

    def _detect_sections(self, normalized_text: str) -> list[dict[str, object]]:
        matches: list[dict[str, object]] = []
        for label, aliases in self.section_aliases.items():
            for alias in aliases:
                for match in re.finditer(self._alias_pattern(alias), normalized_text, re.IGNORECASE):
                    matches.append({"label": label, "start": match.start(), "end": match.end()})
        matches.sort(key=lambda item: int(item["start"]))
        if len({item["label"] for item in matches}) > 1:
            matches.append({"label": "mixed", "start": 0, "end": len(normalized_text)})
        return matches

    def _infer_section(self, metadata: dict[str, object], sections: list[dict[str, object]]) -> str | None:
        span = metadata.get("char_span")
        if isinstance(span, tuple) and span:
            return self._section_for_position(int(span[0]), sections)
        return metadata.get("section") if isinstance(metadata.get("section"), str) else None

    def _section_for_position(self, position: int, sections: list[dict[str, object]]) -> str | None:
        current: str | None = None
        for item in sections:
            if int(item["start"]) <= position:
                current = str(item["label"])
            else:
                break
        return current

    @staticmethod
    def _clean_value(field_name: str, value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value.replace("\n", " ")).strip(" :-,")
        cleaned = re.sub(r"\b(signature|stamp|doctor|hospital|claim form|final bill)\b.*$", "", cleaned, flags=re.IGNORECASE).strip()
        if field_name == "patient_name":
            cleaned = " ".join(part.capitalize() for part in cleaned.split()[:4])
        return cleaned[:80].strip()

    @staticmethod
    def _parse_amount(token: str) -> int | None:
        normalized = token.translate(str.maketrans({"o": "0", "O": "0", "l": "1", "I": "1", ",": ""}))
        digits = re.sub(r"[^\d]", "", normalized)
        if not digits:
            return None
        value = int(digits)
        if value < 1000 or value > 5000000:
            return None
        return value

    def _find_fuzzy_term(self, normalized_text: str, term: str) -> tuple[str, float, int] | None:
        words = normalized_text.split()
        target_tokens = term.split()
        window = len(target_tokens)
        best: tuple[str, float, int] | None = None
        for index in range(0, max(1, len(words) - window + 1)):
            chunk = " ".join(words[index : index + window])
            score = SequenceMatcher(None, chunk, term).ratio()
            if score >= self.fuzzy_threshold and (best is None or score > best[1]):
                char_pos = normalized_text.find(chunk)
                best = (chunk, score, char_pos)
        return best

    @staticmethod
    def _value_appears_in_text(value: str, normalized_text: str) -> bool:
        compact_value = ExtractionRecovery._normalize_text(value)
        return compact_value in normalized_text if compact_value else False

    @staticmethod
    def _normalize_value(value: object) -> str:
        return ExtractionRecovery._normalize_text(str(value))

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = text.lower()
        normalized = normalized.translate(str.maketrans({"|": " ", "_": " ", "@": "a", "$": "s"}))
        normalized = re.sub(r"(?<=[a-z])0(?=[a-z])", "o", normalized)
        normalized = re.sub(r"(?<=[a-z])1(?=[a-z])", "l", normalized)
        normalized = re.sub(r"(?<=[a-z])5(?=[a-z])", "s", normalized)
        normalized = re.sub(r"[\r\t]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    @staticmethod
    def _alias_pattern(alias: str) -> str:
        tokens = [re.escape(token) for token in alias.lower().split()]
        return r"[\s:|._-]*".join(tokens)

    @staticmethod
    def _candidate(
        field_name: str,
        value: object,
        ocr_result: OCRPageResult,
        confidence: float,
        source: str,
        section: str | None,
        metadata: dict[str, object] | None = None,
    ) -> FieldCandidate:
        payload = dict(metadata or {})
        if section:
            payload["section"] = section
        return FieldCandidate(
            field_name=field_name,
            value=value,
            confidence=confidence,
            page_number=ocr_result.page_number,
            bbox=(18, 18, 260, 44),
            source=source,
            metadata=payload,
        )
