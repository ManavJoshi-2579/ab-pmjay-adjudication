"""Field extraction fusion layer."""

from __future__ import annotations

from src.core.state_manager import FieldCandidate, OCRPageResult
from src.extraction.clinical_extractor import ClinicalFieldExtractor
from src.extraction.layoutlm_extractor import LayoutLMFieldExtractor
from src.extraction.recovery import ExtractionRecovery
from src.extraction.regex_backup import RegexBackupExtractor
from src.extraction.table_parser import TableParser


class ExtractionFusion:
    """Fuse multiple extractors while preserving provenance."""

    def __init__(self, config: dict | None = None, thresholds: dict | None = None) -> None:
        self.extractors = [LayoutLMFieldExtractor(), ClinicalFieldExtractor(), RegexBackupExtractor(), TableParser()]
        self.recovery = ExtractionRecovery(config=config, thresholds=thresholds)

    def extract(self, ocr_result: OCRPageResult) -> list[FieldCandidate]:
        """Return deduplicated field candidates."""
        results: list[FieldCandidate] = []
        seen: set[tuple[str, str]] = set()
        for extractor in self.extractors:
            for candidate in extractor.extract(ocr_result):
                key = (candidate.field_name, str(candidate.value).lower())
                if key not in seen:
                    seen.add(key)
                    results.append(candidate)
        return self._score_and_deduplicate(self.recovery.recover(ocr_result, results))

    def is_incomplete(self, candidates: list[FieldCandidate], completeness_threshold: float = 0.8) -> bool:
        """Check whether extracted field set is incomplete."""
        core_fields = ("patient_name", "diagnosis", "procedure", "dates", "amounts")
        present = {candidate.field_name for candidate in candidates}
        coverage = sum(1 for field_name in core_fields if field_name in present) / len(core_fields)
        return coverage < completeness_threshold

    @staticmethod
    def _score_and_deduplicate(candidates: list[FieldCandidate]) -> list[FieldCandidate]:
        """Keep the strongest candidate variants per field/value pair."""
        best: dict[tuple[str, str], FieldCandidate] = {}
        for candidate in candidates:
            key = (candidate.field_name, str(candidate.value).lower())
            current = best.get(key)
            if current is None or candidate.confidence > current.confidence:
                best[key] = candidate
        return sorted(best.values(), key=lambda item: (item.page_number, item.field_name, -item.confidence))
