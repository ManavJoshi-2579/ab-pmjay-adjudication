"""JSON-driven rule engine."""

from __future__ import annotations

from src.core.state_manager import ClassificationResult, FieldCandidate, RuleViolation, TimelineEvent
from src.rules.anomaly_detector import AnomalyDetector
from src.rules.clinical_validator import ClinicalRuleValidator
from src.rules.document_checker import DocumentChecker
from src.rules.stg_loader import STGProfileLoader
from src.rules.stg_validator import STGValidator
from src.timeline.temporal_validator import TemporalValidator


class RuleEngine:
    """Central business rule evaluator."""

    def __init__(self, rules: dict, thresholds: dict) -> None:
        self.rules = rules
        self.thresholds = thresholds
        self.document_checker = DocumentChecker()
        self.temporal_validator = TemporalValidator()
        self.profile_loader = STGProfileLoader()
        self.stg_validator = STGValidator()
        self.clinical_validator = ClinicalRuleValidator()
        self.anomaly_detector = AnomalyDetector()
        self.last_evaluation: dict = {}

    def evaluate(
        self,
        claim_type: str,
        classifications: list[ClassificationResult],
        fields: dict[str, list[FieldCandidate]],
        timeline: list[TimelineEvent],
        ocr_results: list | None = None,
    ) -> list[RuleViolation]:
        """Run all applicable rules and collect violations."""
        violations: list[RuleViolation] = []
        profile = self.profile_loader.select_profile(self.rules, claim_type, fields)
        required_documents = profile.get("required_documents") or self.rules.get("required_documents", {}).get(claim_type, [])
        fields_by_page: dict[int, list[FieldCandidate]] = {}
        for values in fields.values():
            for item in values:
                fields_by_page.setdefault(item.page_number, []).append(item)

        document_violations, document_summary = self.document_checker.validate(required_documents, classifications, fields_by_page)
        violations.extend(document_violations)

        temporal_violations = self.temporal_validator.validate(
            timeline,
            max_length_of_stay_days=self.thresholds.get("rules", {}).get("max_length_of_stay_days", 30),
            date_order_rules=self.rules.get("date_order", []),
        )
        violations.extend(temporal_violations)

        stg_violations, stg_summary = self.stg_validator.validate(fields, profile)
        violations.extend(stg_violations)

        clinical_violations, clinical_summary = self.clinical_validator.validate(fields, profile)
        violations.extend(clinical_violations)

        anomaly_violations = self.anomaly_detector.validate(fields, self.rules.get("amount_rules", {}), ocr_results=ocr_results)
        violations.extend(anomaly_violations)

        self.last_evaluation = {
            "selected_package": {
                "package_id": profile.get("package_id"),
                "package_name": profile.get("package_name"),
                "selection_score": profile.get("selection_score", 0.0),
                "source_type": profile.get("source_type", "config"),
                "source_document": profile.get("source_document", ""),
                "required_documents": required_documents,
            },
            "documents": document_summary,
            "rules": {
                "stg_alignment": stg_summary,
                "clinical_rules": clinical_summary,
                "temporal_rule_count": len(temporal_violations),
                "anomaly_rule_count": len(anomaly_violations),
            },
            "violations": [
                {"rule_name": item.rule_name, "severity": item.severity, "message": item.message}
                for item in violations
            ],
        }
        return violations

    def summary(self) -> dict:
        """Return last evaluation summary for explainability and payload shaping."""
        return self.last_evaluation
