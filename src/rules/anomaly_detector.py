"""Detect document anomalies."""

from __future__ import annotations

from difflib import SequenceMatcher

from src.core.state_manager import FieldCandidate, RuleViolation


class AnomalyDetector:
    """Detect unusual extracted values."""

    def validate(self, fields: dict[str, list[FieldCandidate]], amount_rules: dict, ocr_results: list | None = None) -> list[RuleViolation]:
        """Check amount anomalies."""
        violations: list[RuleViolation] = []
        max_amount = amount_rules.get("max_claim_amount", 500000)
        require_positive = amount_rules.get("require_positive_amount", True)
        for item in fields.get("amounts", []):
            value = float(item.value)
            if require_positive and value <= 0:
                violations.append(
                    RuleViolation(
                        rule_name="positive_amount",
                        severity="high",
                        message=f"Invalid non-positive amount: {value}",
                    )
                )
            if value > max_amount:
                violations.append(
                    RuleViolation(
                        rule_name="max_claim_amount",
                        severity="medium",
                        message=f"Amount {value} exceeds configured maximum {max_amount}.",
                    )
                )
        if ocr_results:
            duplicate_reports = self._duplicate_reports(ocr_results)
            if duplicate_reports:
                violations.append(
                    RuleViolation(
                        rule_name="duplicate_report_content",
                        severity="medium",
                        message="Potential duplicate or reused report content detected across submitted pages.",
                        evidence=duplicate_reports,
                    )
                )
        return violations

    @staticmethod
    def _duplicate_reports(ocr_results: list) -> list[dict]:
        normalized = []
        for item in ocr_results:
            text = " ".join(item.full_text.lower().split())
            if len(text) >= 40:
                normalized.append((item.page_number, text))
        duplicates: list[dict] = []
        for index, (page_a, text_a) in enumerate(normalized):
            for page_b, text_b in normalized[index + 1 :]:
                similarity = SequenceMatcher(None, text_a[:500], text_b[:500]).ratio()
                if similarity >= 0.96:
                    duplicates.append({"page_a": page_a, "page_b": page_b, "similarity": round(similarity, 3)})
        return duplicates
