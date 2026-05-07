from __future__ import annotations

from src.core.state_manager import OCRPageResult
from src.extraction.fusion import ExtractionFusion


def _ocr(page_number: int, text: str) -> OCRPageResult:
    return OCRPageResult(
        page_number=page_number,
        full_text=text,
        words=[],
        confidence=0.8,
        source="test",
        image_path="test.png",
    )


def test_extraction_recovers_fragmented_and_fuzzy_fields() -> None:
    extractor = ExtractionFusion(
        config={
            "field_aliases": {
                "patient_name": ["patient name"],
                "diagnosis": ["diagnosis"],
                "procedure": ["procedure"],
                "amounts": ["total amount"],
                "dates": ["date"],
            },
            "field_vocab": {
                "diagnosis": ["appendicitis"],
                "procedure": ["appendectomy"],
            },
            "section_aliases": {"claim_form": ["claim form"], "bill": ["final bill"]},
        },
        thresholds={"min_field_confidence": 0.6, "fuzzy_match_threshold": 0.82},
    )
    text = "Claim Form Patient Name: joHN doE Diagn0sis appendicitis Procedure appendect0my Date 2026-04-18"
    fields = extractor.extract(_ocr(1, text))
    by_name = {item.field_name: item for item in fields}
    assert by_name["patient_name"].value == "John Doe"
    assert by_name["diagnosis"].value.lower() == "appendicitis"
    assert "append" in by_name["procedure"].value.lower()
    assert by_name["dates"].value == "2026-04-18"


def test_extraction_avoids_losing_billed_amount_in_mixed_page() -> None:
    extractor = ExtractionFusion()
    text = (
        "Discharge Summary Final Diagnosis Appendicitis "
        "Final Bill Total Amount Rs 45O00 Procedure Appendectomy"
    )
    fields = extractor.extract(_ocr(1, text))
    amounts = [item for item in fields if item.field_name == "amounts"]
    assert amounts
    assert any(item.value == 45000 for item in amounts)
    assert any(item.metadata.get("section") in {"bill", "mixed"} for item in amounts)
