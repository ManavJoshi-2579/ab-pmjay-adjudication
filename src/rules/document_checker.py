"""Document completeness checks."""

from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher

from src.core.state_manager import ClassificationResult, RuleViolation


class DocumentChecker:
    """Validate presence of required document classes."""

    def validate(
        self,
        required_documents: list[str],
        classifications: list[ClassificationResult],
        fields_by_page: dict[int, list],
    ) -> tuple[list[RuleViolation], dict]:
        """Check missing required document types."""
        labels = {classification.label for classification in classifications}
        missing = [label for label in required_documents if label not in labels]
        violations: list[RuleViolation] = []
        summary = {
            "required_documents": required_documents,
            "found_documents": sorted(labels),
            "missing_documents": missing,
            "identity_consistency": {"status": "pass", "values": []},
        }
        if missing:
            violations.append(
                RuleViolation(
                    rule_name="required_documents",
                    severity="high",
                    message=f"Missing required documents: {', '.join(missing)}",
                    evidence=[{"expected": label} for label in missing],
                )
            )
        duplicates = self._duplicate_documents(classifications)
        if duplicates:
            violations.append(
                RuleViolation(
                    rule_name="duplicate_documents",
                    severity="medium",
                    message=f"Duplicate document classes detected: {', '.join(duplicates)}",
                    evidence=[{"label": label} for label in duplicates],
                )
            )
        identity_violation = self._validate_identity_consistency(fields_by_page)
        if identity_violation:
            violations.append(identity_violation)
            summary["identity_consistency"] = {
                "status": "fail",
                "values": identity_violation.evidence,
            }
        else:
            summary["identity_consistency"] = {
                "status": "pass",
                "values": self._identity_values(fields_by_page),
            }
        return violations, summary

    @staticmethod
    def _duplicate_documents(classifications: list[ClassificationResult]) -> list[str]:
        """Return duplicated document labels excluding benign others."""
        counts: dict[str, int] = {}
        for item in classifications:
            counts[item.label] = counts.get(item.label, 0) + 1
        return sorted(label for label, count in counts.items() if count > 1 and label != "other")

    def _validate_identity_consistency(self, fields_by_page: dict[int, list]) -> RuleViolation | None:
        identities = self._identity_values(fields_by_page)
        names = [item["value"] for item in identities if item["field"] == "patient_name"]
        ids = [item["value"] for item in identities if item["field"] in {"patient_id", "claim_id"}]
        inconsistent_names = self._has_inconsistency(names)
        inconsistent_ids = self._has_inconsistency(ids)
        if inconsistent_names or inconsistent_ids:
            return RuleViolation(
                rule_name="patient_identity_mismatch",
                severity="high",
                message="Patient identity is inconsistent across supplied documents.",
                evidence=identities,
            )
        return None

    @staticmethod
    def _identity_values(fields_by_page: dict[int, list]) -> list[dict]:
        values: list[dict] = []
        for page_number, items in fields_by_page.items():
            for item in items:
                if item.field_name in {"patient_name", "patient_id", "claim_id"}:
                    values.append(
                        {
                            "page_number": page_number,
                            "field": item.field_name,
                            "value": DocumentChecker._normalize_identity_value(item.field_name, str(item.value)),
                        }
                    )
        return values

    @staticmethod
    def _has_inconsistency(values: list[str]) -> bool:
        normalized = [value.strip().lower() for value in values if value]
        if len(normalized) <= 1:
            return False
        most_common = Counter(normalized).most_common(1)[0][0]
        return any(SequenceMatcher(None, value, most_common).ratio() < 0.86 for value in normalized)

    @staticmethod
    def _normalize_identity_value(field_name: str, value: str) -> str:
        normalized = value.strip()
        if field_name == "patient_name":
            tokens = [
                token for token in normalized.split()
                if token.lower() not in {
                    "admission",
                    "date",
                    "diagnosis",
                    "procedure",
                    "discharge",
                    "summary",
                    "claim",
                    "form",
                    "final",
                    "note",
                    "surgeon",
                }
            ]
            normalized = " ".join(tokens[:4])
        return normalized
