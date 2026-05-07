from __future__ import annotations

from pathlib import Path

from src.core.state_manager import FieldCandidate
from src.rules.stg_document_parser import STGDocumentParser
from src.rules.stg_loader import STGProfileLoader


def test_stg_document_parser_extracts_realistic_sections(tmp_path: Path) -> None:
    source = tmp_path / "appendicitis_stg.txt"
    source.write_text(
        "\n".join(
            [
                "Package Name: Appendicitis Appendectomy",
                "Mandatory Documents: Claim Form, Discharge Summary, Procedure Note, Final Bill",
                "Clinical Conditions: Diagnosis - appendicitis",
                "Required Investigations: Ultrasound abdomen, blood test",
                "Thresholds: Hb >= 7",
            ]
        ),
        encoding="utf-8",
    )
    parser = STGDocumentParser()
    parsed = parser.parse_path(str(source), claim_types=["surgery_claim"])
    assert parsed is not None
    assert parsed.package_name == "Appendicitis Appendectomy"
    assert set(parsed.required_documents) == {"claim_form", "discharge_summary", "procedure_note", "bill"}
    assert "ultrasound" in parsed.investigations
    assert any(rule["field"] == "hemoglobin" for rule in parsed.clinical_rules)


def test_loader_prefers_stg_documents_and_matches_package(tmp_path: Path) -> None:
    source = tmp_path / "fever_stg.txt"
    source.write_text(
        "\n".join(
            [
                "Medical Package: Fever Medical Management",
                "Required Documents: Claim Form, Discharge Summary, Bill",
                "Clinical Criteria: Diagnosis: fever",
                "Thresholds: fever duration >= 3 days",
            ]
        ),
        encoding="utf-8",
    )
    loader = STGProfileLoader()
    rules = {
        "stg_documents": [{"path": str(source), "claim_types": ["medical_claim"]}],
        "stg_packages": [
            {
                "package_id": "fallback",
                "package_name": "Fallback",
                "claim_types": ["medical_claim"],
                "match": {"diagnosis_any": ["fallback"], "procedure_any": []},
            }
        ],
        "required_documents": {"medical_claim": ["claim_form", "discharge_summary", "bill"]},
    }
    fields = {
        "diagnosis": [
            FieldCandidate(
                field_name="diagnosis",
                value="Fever",
                confidence=0.9,
                page_number=1,
                bbox=(0, 0, 1, 1),
                source="test",
            )
        ]
    }
    profile = loader.select_profile(rules, "medical_claim", fields)
    assert profile["package_name"] == "Fever Medical Management"
    assert profile["source_type"] == "stg_document"
    assert any(rule["field"] == "fever_duration_days" for rule in profile["clinical_rules"])
