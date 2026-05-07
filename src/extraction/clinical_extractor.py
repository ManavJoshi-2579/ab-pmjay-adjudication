"""Clinical and identity field extraction."""

from __future__ import annotations

import re

from src.core.state_manager import FieldCandidate, OCRPageResult


class ClinicalFieldExtractor:
    """Extract identity, clinical thresholds, and evidence-friendly fields."""

    def extract(self, ocr_result: OCRPageResult) -> list[FieldCandidate]:
        text = ocr_result.full_text
        normalized = text.lower()
        candidates: list[FieldCandidate] = []

        patterns = [
            ("claim_id", r"(?:claim[\s_-]*id|claim no)[:\s#-]+([a-z0-9-]{4,32})", self._identity),
            ("patient_id", r"(?:patient[\s_-]*id|uhid|beneficiary[\s_-]*id)[:\s#-]+([a-z0-9-]{4,32})", self._identity),
            ("admission_date", r"(?:admission date|date of admission)[:\s-]+(20\d{2}[-/]\d{2}[-/]\d{2})", self._date),
            ("discharge_date", r"(?:discharge date|date of discharge)[:\s-]+(20\d{2}[-/]\d{2}[-/]\d{2})", self._date),
            ("procedure_date", r"(?:procedure date|surgery date|operation date|date of procedure)[:\s-]+(20\d{2}[-/]\d{2}[-/]\d{2})", self._date),
            ("hemoglobin", r"(?:hemoglobin|haemoglobin|hb)[\s:=<>-]+(\d+(?:\.\d+)?)", float),
            (
                "fever_duration_days",
                r"(?:fever duration|duration of fever|fever for)[\s:=<>-]+(\d+(?:\.\d+)?)\s*(?:day|days)?",
                self._days,
            ),
        ]
        for field_name, pattern, caster in patterns:
            for match in re.finditer(pattern, normalized, re.IGNORECASE):
                value = caster(match.group(1))
                candidates.append(
                    FieldCandidate(
                        field_name=field_name,
                        value=value,
                        confidence=0.83 if field_name not in {"hemoglobin", "fever_duration_days"} else 0.8,
                        page_number=ocr_result.page_number,
                        bbox=(24, 24, 280, 48),
                        source="clinical_extractor",
                        metadata={"char_span": match.span(), "pattern": field_name},
                    )
                )

        imaging_match = re.search(
            r"(?:imaging|x-ray|xray|ct|mri|ultrasound|usg|scan|radiology)[\s:,-]+([a-z0-9 ,./()-]{6,100})",
            normalized,
            re.IGNORECASE,
        )
        if imaging_match:
            candidates.append(
                FieldCandidate(
                    field_name="imaging_findings",
                    value=self._phrase(imaging_match.group(1)),
                    confidence=0.77,
                    page_number=ocr_result.page_number,
                    bbox=(24, 24, 280, 48),
                    source="clinical_extractor",
                    metadata={"char_span": imaging_match.span(), "pattern": "imaging_findings"},
                )
            )

        if any(token in normalized for token in ("report no", "lab report", "radiology report", "investigation report")):
            report_id_match = re.search(r"(?:report[\s_-]*no|report id)[:\s#-]+([a-z0-9-]{4,32})", normalized, re.IGNORECASE)
            if report_id_match:
                candidates.append(
                    FieldCandidate(
                        field_name="report_id",
                        value=self._identity(report_id_match.group(1)),
                        confidence=0.8,
                        page_number=ocr_result.page_number,
                        bbox=(24, 24, 280, 48),
                        source="clinical_extractor",
                        metadata={"char_span": report_id_match.span(), "pattern": "report_id"},
                    )
                )

        return candidates

    @staticmethod
    def _identity(value: str) -> str:
        return value.strip().upper()

    @staticmethod
    def _date(value: str) -> str:
        return value.replace("/", "-")

    @staticmethod
    def _days(value: str) -> int:
        return int(float(value))

    @staticmethod
    def _phrase(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip(" ,.-").title()
