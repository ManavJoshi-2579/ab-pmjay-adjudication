from __future__ import annotations

from src.core.state_manager import ClassificationResult, FieldCandidate, OCRPageResult, TimelineEvent
from src.rules.engine import RuleEngine


def _field(field_name: str, value: object, page_number: int = 1) -> FieldCandidate:
    return FieldCandidate(
        field_name=field_name,
        value=value,
        confidence=0.9,
        page_number=page_number,
        bbox=(0, 0, 10, 10),
        source="test",
    )


def test_rule_engine_fails_missing_required_document_and_identity_mismatch() -> None:
    rules = {
        "required_documents": {"surgery_claim": ["claim_form", "discharge_summary", "bill"]},
        "date_order": [],
        "amount_rules": {"max_claim_amount": 500000, "require_positive_amount": True},
        "stg_packages": [],
    }
    thresholds = {"rules": {"max_length_of_stay_days": 30}}
    engine = RuleEngine(rules, thresholds)
    violations = engine.evaluate(
        "surgery_claim",
        [
            ClassificationResult(page_number=1, label="claim_form", confidence=0.9),
            ClassificationResult(page_number=2, label="discharge_summary", confidence=0.9),
        ],
        {
            "patient_name": [_field("patient_name", "John Doe", 1), _field("patient_name", "Jane Doe", 2)],
            "amounts": [_field("amounts", 10000, 2)],
        },
        [TimelineEvent(event_type="admission", date="2026-04-18", page_number=1, confidence=0.8, evidence="")],
        [OCRPageResult(page_number=1, full_text="Claim form john doe", words=[], confidence=0.8, source="test", image_path="a")],
    )
    rule_names = {item.rule_name for item in violations}
    assert "required_documents" in rule_names
    assert "patient_identity_mismatch" in rule_names


def test_rule_engine_applies_generic_clinical_rules_from_profile() -> None:
    rules = {
        "required_documents": {"medical_claim": ["claim_form", "discharge_summary", "bill"]},
        "date_order": [],
        "amount_rules": {"max_claim_amount": 500000, "require_positive_amount": True},
        "stg_packages": [
            {
                "package_id": "fever_medical_management",
                "package_name": "Fever Medical Management",
                "claim_types": ["medical_claim"],
                "match": {"diagnosis_any": ["fever"], "procedure_any": []},
                "required_documents": ["claim_form", "discharge_summary", "bill"],
                "clinical_rules": [
                    {"rule_id": "fever_duration_min_days", "field": "fever_duration_days", "operator": ">=", "value": 3, "severity": "high"},
                    {"rule_id": "hemoglobin_safe_floor", "field": "hemoglobin", "operator": ">=", "value": 7, "severity": "high"},
                ],
            }
        ],
    }
    thresholds = {"rules": {"max_length_of_stay_days": 30}}
    engine = RuleEngine(rules, thresholds)
    violations = engine.evaluate(
        "medical_claim",
        [
            ClassificationResult(page_number=1, label="claim_form", confidence=0.9),
            ClassificationResult(page_number=2, label="discharge_summary", confidence=0.9),
            ClassificationResult(page_number=3, label="bill", confidence=0.9),
        ],
        {
            "diagnosis": [_field("diagnosis", "Fever", 1)],
            "fever_duration_days": [_field("fever_duration_days", 2, 2)],
            "hemoglobin": [_field("hemoglobin", 6.5, 2)],
            "amounts": [_field("amounts", 10000, 3)],
        },
        [
            TimelineEvent(event_type="admission", date="2026-04-18", page_number=1, confidence=0.8, evidence=""),
            TimelineEvent(event_type="discharge", date="2026-04-20", page_number=2, confidence=0.8, evidence=""),
        ],
        [OCRPageResult(page_number=1, full_text="fever claim", words=[], confidence=0.8, source="test", image_path="a")],
    )
    rule_names = {item.rule_name for item in violations}
    assert "fever_duration_min_days" in rule_names
    assert "hemoglobin_safe_floor" in rule_names
