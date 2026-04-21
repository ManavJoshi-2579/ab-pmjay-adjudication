"""Generate synthetic placeholder documents."""

from __future__ import annotations

import json
import shutil
from pathlib import Path


def main() -> None:
    """Create synthetic document placeholders."""
    root = Path("data/synthetic")
    input_root = Path("data/input/generated_claims")
    root.mkdir(parents=True, exist_ok=True)
    if input_root.exists():
        shutil.rmtree(input_root)
    input_root.mkdir(parents=True, exist_ok=True)
    scenarios = [
        {
            "claim_id": "synthetic-appendectomy-001",
            "scenario": "baseline",
            "claim_type": "surgery_claim",
            "documents": [
                {
                    "file": "claim_form.png",
                    "text_hint": "Claim Form Patient Name John Doe Admission Date 2026-04-18 Diagnosis Appendicitis",
                },
                {
                    "file": "discharge_summary.png",
                    "text_hint": "Discharge Summary Patient Name John Doe Diagnosis Appendicitis Procedure Appendectomy Discharge Date 2026-04-20 Signature Stamp",
                },
                {
                    "file": "procedure_note.png",
                    "text_hint": "Procedure Note Procedure Appendectomy Date 2026-04-19 Surgeon Signature",
                },
                {
                    "file": "bill.png",
                    "text_hint": "Final Bill Amount 45000 Date 2026-04-20 Stamp",
                },
            ],
        },
        {
            "claim_id": "synthetic-missing-fields-001",
            "scenario": "missing_fields",
            "claim_type": "surgery_claim",
            "documents": [
                {
                    "file": "missing_claim_form.png",
                    "text_hint": "Claim Form Patient Name John Doe Admission Date 2026-04-18",
                },
                {
                    "file": "missing_bill.png",
                    "text_hint": "Final Bill Date 2026-04-20",
                },
            ],
        },
        {
            "claim_id": "synthetic-wrong-sequence-001",
            "scenario": "wrong_sequence",
            "claim_type": "surgery_claim",
            "documents": [
                {
                    "file": "wrong_claim_form.png",
                    "text_hint": "Claim Form Patient Name John Doe Admission Date 2026-04-20 Diagnosis Appendicitis",
                },
                {
                    "file": "wrong_discharge_summary.png",
                    "text_hint": "Discharge Summary Patient Name John Doe Diagnosis Appendicitis Procedure Appendectomy Discharge Date 2026-04-18 Signature Stamp",
                },
            ],
        },
        {
            "claim_id": "synthetic-extra-docs-001",
            "scenario": "extra_documents",
            "claim_type": "surgery_claim",
            "documents": [
                {
                    "file": "extra_claim_form.png",
                    "text_hint": "Claim Form Patient Name John Doe Admission Date 2026-04-18 Diagnosis Appendicitis",
                },
                {
                    "file": "extra_discharge_summary.png",
                    "text_hint": "Discharge Summary Patient Name John Doe Diagnosis Appendicitis Procedure Appendectomy Discharge Date 2026-04-20 Signature Stamp",
                },
                {
                    "file": "extra_other.png",
                    "text_hint": "Other Miscellaneous Hospital Circular",
                },
            ],
        },
        {
            "claim_id": "synthetic-class-specific-001",
            "scenario": "class_specific_documents",
            "claim_type": "surgery_claim",
            "documents": [
                {
                    "file": "class_claim_form.png",
                    "text_hint": "Claim Form Claim ID PMJAY123 Patient Name Riya Sharma Admission Date 2026-03-04 Preauth Approved",
                },
                {
                    "file": "class_discharge_summary.png",
                    "text_hint": "Discharge Summary Final Diagnosis Fracture Procedure ORIF Date of Discharge 2026-03-09",
                },
                {
                    "file": "class_procedure_note.png",
                    "text_hint": "Procedure Note Operation Note Surgeon Dr Rao Procedure ORIF Date 2026-03-05",
                },
                {
                    "file": "class_bill.png",
                    "text_hint": "Final Bill Invoice Total Amount INR 78000 Date 2026-03-09",
                },
            ],
        },
        {
            "claim_id": "synthetic-noisy-ocr-001",
            "scenario": "noisy_ocr",
            "claim_type": "surgery_claim",
            "documents": [
                {
                    "file": "noisy_discharge.png",
                    "text_hint": "D1scharge Summ@ry Pat1ent Name J0hn D0e Diagn0sis Appendicitis Pr0cedure Appendectomy D1scharge Date 2026-04-20 Signatvre",
                },
                {
                    "file": "noisy_bill.png",
                    "text_hint": "Fina1 Bi11 Amount INR 45OOO Date 2026-04-20 Starnp",
                },
            ],
        },
        {
            "claim_id": "synthetic-conflicting-data-001",
            "scenario": "conflicting_data",
            "claim_type": "surgery_claim",
            "documents": [
                {
                    "file": "conflict_claim_form.png",
                    "text_hint": "Claim Form Patient Name John Doe Admission Date 2026-04-18 Diagnosis Cataract",
                },
                {
                    "file": "conflict_procedure_note.png",
                    "text_hint": "Procedure Note Procedure Appendectomy Date 2026-04-19 Surgeon Signature",
                },
                {
                    "file": "conflict_bill.png",
                    "text_hint": "Invoice Total Amount 65000 Date 2026-04-20",
                },
            ],
        },
        {
            "claim_id": "synthetic-confusing-structure-001",
            "scenario": "confusing_structure",
            "claim_type": "surgery_claim",
            "documents": [
                {
                    "file": "confusing_table_doc.png",
                    "text_hint": "Patient Name Ravi Kumar | Date 2026-04-11 | Amount 55000 | Procedure Appendectomy | Final Bill",
                },
                {
                    "file": "confusing_discharge_table.png",
                    "text_hint": "Discharge Summary Table Diagnosis Appendicitis Date of Discharge 2026-04-12 Ward Monitoring",
                },
            ],
        },
        {
            "claim_id": "synthetic-no-header-001",
            "scenario": "removed_headers",
            "claim_type": "medical_claim",
            "documents": [
                {
                    "file": "headerless_claim.png",
                    "text_hint": "Patient Name Meera Singh Admission Date 2026-02-10 Beneficiary ID PMJAY88",
                },
                {
                    "file": "headerless_bill.png",
                    "text_hint": "Invoice Total Amount 34000 Date 2026-02-13 Payment Pending",
                },
            ],
        },
        {
            "claim_id": "synthetic-mixed-document-001",
            "scenario": "mixed_document",
            "claim_type": "surgery_claim",
            "documents": [
                {
                    "file": "mixed_doc.png",
                    "text_hint": "Discharge Summary Patient Name John Doe Procedure Appendectomy Invoice Total Amount 45000 Date of Discharge 2026-04-20",
                }
            ],
        },
        {
            "claim_id": "synthetic-misleading-layout-001",
            "scenario": "misleading_layout",
            "claim_type": "surgery_claim",
            "documents": [
                {
                    "file": "misleading_table.png",
                    "text_hint": "Table Row1 Procedure ORIF Row2 Surgeon Dr Shah Row3 Amount 67000 Row4 Date 2026-06-11",
                },
                {
                    "file": "misleading_summary.png",
                    "text_hint": "Final Diagnosis Cataract Monitoring Ward Sheet Date 2026-06-12",
                },
            ],
        },
        {
            "claim_id": "synthetic-block-mixed-001",
            "scenario": "block_level_mixed",
            "claim_type": "surgery_claim",
            "documents": [
                {
                    "file": "block_mixed.png",
                    "text_hint": "Claim Form Patient Name Arjun Rao Admission Date 2026-07-01 | Procedure Note Surgeon Dr Das Procedure ORIF Date 2026-07-02 | Final Bill Amount 56000 Date 2026-07-04",
                }
            ],
        },
        {
            "claim_id": "synthetic-fuzzy-ocr-001",
            "scenario": "fuzzy_ocr_noise",
            "claim_type": "surgery_claim",
            "documents": [
                {
                    "file": "fuzzy_discharge.png",
                    "text_hint": "D1scharg3 Summ@ry Fina1 Diagnos1s Appendicitis Date 2026-08-11",
                },
                {
                    "file": "fuzzy_procedure.png",
                    "text_hint": "Pr0cedure N0te 0peration N0te Surge0n Dr Sen Pr0cedure Appendectomy Date 2026-08-10",
                },
            ],
        },
        {
            "claim_id": "synthetic-clinical-violation-001",
            "scenario": "clinical_violation",
            "claim_type": "medical_claim",
            "documents": [
                {
                    "file": "claim_form.png",
                    "text_hint": "Claim Form Claim ID PMJAY2001 Patient Name Ravi Kumar Admission Date 2026-05-10 Diagnosis Fever",
                },
                {
                    "file": "discharge_summary.png",
                    "text_hint": "Discharge Summary Patient Name Ravi Kumar Final Diagnosis Fever Discharge Date 2026-05-12 Hemoglobin 6 Fever Duration 2 days",
                },
                {
                    "file": "bill.png",
                    "text_hint": "Final Bill Invoice Total Amount INR 12000 Date 2026-05-12",
                },
            ],
        },
    ]
    for scenario in scenarios:
        claim_dir = input_root / scenario["claim_id"]
        claim_dir.mkdir(parents=True, exist_ok=True)
        for document in scenario["documents"]:
            target = root / document["file"]
            target.touch(exist_ok=True)
            target.with_suffix(".txt").write_text(document["text_hint"], encoding="utf-8")
            claim_target = claim_dir / document["file"]
            claim_target.touch(exist_ok=True)
            claim_target.with_suffix(".txt").write_text(document["text_hint"], encoding="utf-8")
        (claim_dir / "claim.json").write_text(
            json.dumps(
                {
                    "claim_id": scenario["claim_id"],
                    "scenario": scenario["scenario"],
                    "claim_type": scenario["claim_type"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    (root / "manifest.json").write_text(json.dumps({"scenarios": scenarios}, indent=2), encoding="utf-8")
    (input_root / "manifest.json").write_text(json.dumps({"scenarios": scenarios}, indent=2), encoding="utf-8")
    print(f"Synthetic placeholders generated in {root} and staged in {input_root}")


if __name__ == "__main__":
    main()
