# Demo Notes

## Demo Goal

Show that the system can ingest claim packets, validate them using STG-aware logic, and return explainable adjudication outcomes that support fraud-aware healthcare review.

## Step-By-Step Demo Flow

1. Open the repository root and README to frame the problem, solution, and architecture.
2. Show `data/input/qa_cases/` and `data/input/generated_claims/` to establish the curated and synthetic demo scenarios.
3. Run synthetic generation to refresh demo inputs.
4. Run the main pipeline to process all sample and synthetic claims.
5. Open generated outputs and compare a passing case with failing cases.
6. Highlight how the reasons and evidence justify each decision.

## Commands To Run

```bash
python scripts/generate_synthetic.py
python -B main.py
```

Optional supporting command:

```bash
pytest
```

## What Outputs To Show

- Console summary from `python -B main.py` showing pass/fail decisions across scenarios.
- `outputs/final_json/` for adjudication JSON payloads.
- `outputs/debug/` for deeper diagnostic traces.
- `outputs/visualizations/` or claim-level evidence text files for human-readable explanation artifacts.

## Suggested Demo Sequence

1. Show `valid_claim` as the baseline passing scenario.
2. Show `missing_document` to demonstrate incomplete packet detection.
3. Show `clinical_violation` to demonstrate medical-rule enforcement.
4. Show `stg_doc_claim` to emphasize STG-backed validation.
5. Mention one synthetic edge case such as noisy OCR or conflicting data to demonstrate resilience.

## Talking Points

- STG-driven: The system does not rely on a static checklist alone. It uses treatment-guideline documents and configurable rules to evaluate claim appropriateness.
- Explainable decisions: Every adjudication is accompanied by reasons, evidence, and debug artifacts so a reviewer can understand why a case passed or failed.
- Fraud-aware system: Missing documents, contradictory signals, suspicious chronology, and inconsistent clinical narratives are surfaced as structured adjudication risks.

## Judge-Friendly Summary

This demo shows a practical adjudication workflow rather than a disconnected model showcase. The value is in combining OCR, extraction, timeline reasoning, STG validation, and explainability into one workflow that behaves like a production claims review assistant.
