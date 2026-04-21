# NHA STG-Based Adjudication System

Production-ready, STG-driven AI system for automated healthcare claim adjudication under PMJAY.

An explainable, production-style claim adjudication pipeline for PMJAY/NHA workflows that reads healthcare claim packets, reconstructs evidence across documents, validates them against Standard Treatment Guidelines, and produces auditable pass/fail decisions.

## Problem Statement

Healthcare claim review is slow, document-heavy, and difficult to standardize. Adjudicators must inspect claim forms, discharge summaries, procedure notes, and bills, then decide whether the record is complete, clinically consistent, and aligned with treatment guidelines. That creates delay, inconsistency, and room for fraud or avoidable reimbursement error.

## Solution Overview

This repository presents a modular adjudication system that ingests claim documents, applies OCR and document understanding, extracts structured evidence, reconstructs the patient timeline, validates the packet against STG-based rules, and returns an explainable decision with reasons and confidence.

This system mirrors real NHA adjudication workflows, including document sufficiency checks, clinical validation, and STG alignment.

The goal is not a narrow, single-procedure checker. It is a procedure-agnostic STG-driven system designed to generalize across claim types while keeping the decision path transparent.

The system prioritizes safe adjudication, ensuring uncertain or inconsistent claims are flagged instead of incorrectly approved.

## Why This Solution Stands Out

- Procedure-agnostic: scales across PMJAY packages instead of being limited to one procedure flow.
- STG-driven: relies on configurable treatment-guideline logic, not just hardcoded rules.
- Explainable: returns decision, evidence, and reasoning for each adjudication outcome.
- Fail-safe: prioritizes flagging risky or inconsistent claims over unsafe approvals.
- Production-ready: delivers an end-to-end pipeline from document intake to auditable output.

## Key Features

- OCR-ready pipeline with OCR adapters and safe local fallbacks.
- Document classification across heterogeneous claim packet inputs.
- Structured extraction of clinical, billing, and timeline evidence.
- STG-driven validation using configurable rules and treatment-guideline documents.
- Rule engine for document sufficiency, chronology, anomaly, and clinical checks.
- Decision engine that consolidates signals into a final adjudication with confidence.
- Explainability layer that surfaces reasons, evidence, and reviewer-friendly traces.

## Quick Demo

Run these two commands to verify the system quickly:

```bash
python scripts/generate_synthetic.py
python -B main.py
```

What judges should observe:

- `valid_claim` -> `Pass`
- `missing_document` -> `Fail`
- `clinical_violation` -> `Fail`

This gives a fast view of baseline approval, missing-evidence detection, and clinical-rule enforcement.

## System Flow

```text
Claim Packet
    ->
OCR / Text Recovery
    ->
Document Classification
    ->
Field Extraction + Timeline Reconstruction
    ->
STG Validation + Rule Engine Checks
    ->
Decision Engine
    ->
Explainable JSON Output + Evidence Trace
```

## How To Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Generate synthetic evaluation cases:

```bash
python scripts/generate_synthetic.py
```

Run the full adjudication pipeline:

```bash
python -B main.py
```

Optional supporting commands:

```bash
pytest
uvicorn api.app:app --reload
```

## Project Structure

```text
.
|-- api/                 FastAPI interface for serving adjudication results
|-- configs/             Pipeline, threshold, and rule configuration
|-- data/
|   |-- input/           Sample and generated claim packets
|   |-- stg/             STG source documents used by validation
|   `-- synthetic/       Synthetic source fixtures for demo scenarios
|-- docs/                Demo walkthrough and submission notes
|-- evaluation/          Validation and scoring utilities
|-- scripts/             Synthetic generation and helper scripts
|-- src/
|   |-- classification/  Document classification logic
|   |-- core/            Pipeline orchestration and state handling
|   |-- decision/        Confidence scoring and final decisioning
|   |-- explainability/  Evidence tracing and reporting
|   |-- extraction/      Structured data extraction
|   |-- ocr/             OCR adapters and ensemble wrappers
|   |-- recovery/        Fallback and low-confidence recovery logic
|   |-- rules/           STG parsing, rule engine, anomaly checks
|   |-- timeline/        Event extraction and temporal validation
|   `-- vision/          Vision-stage utilities
|-- tests/               Pipeline and rule validation tests
|-- README.md
`-- main.py              Main batch entrypoint
```

## Validation Scenarios

Representative cases included in the repository:

- `valid_claim`: clean packet expected to pass.
- `missing_document`: incomplete supporting evidence.
- `clinical_violation`: medically inconsistent or clinically unsafe record.
- `stg_doc_claim`: demonstrates STG-backed validation.
- Synthetic edge cases for noisy OCR, conflicting data, wrong sequence, mixed documents, and misleading layouts.

## Output Example

Example adjudication output (structured, explainable, and auditable):

```json
{
  "claim_id": "valid_claim",
  "documents": [
    {
      "document_type": "claim_form",
      "confidence": 0.96
    }
  ],
  "timeline": [
    {
      "event": "admission",
      "date": "2026-04-18"
    },
    {
      "event": "procedure",
      "date": "2026-04-19"
    }
  ],
  "decision": {
    "status": "Pass",
    "confidence": 0.8805,
    "reasons": [
      "Required documents detected",
      "Timeline is clinically consistent",
      "Claim aligns with STG-supported expectations"
    ],
    "evidence": [
      "procedure_note",
      "discharge_summary",
      "bill"
    ]
  }
}
```

## Key Differentiator

This project is built as a procedure-agnostic STG-driven system. Instead of hardcoding a single use case, it validates claim packets through configurable treatment-guideline logic, making the architecture more extensible, reusable, and suitable for real adjudication workflows.

## Impact

- Reduces manual review effort for high-volume healthcare claims.
- Improves consistency through configurable STG and rule logic.
- Increases reviewer trust through explainable outputs rather than opaque scoring.
- Helps surface fraud, missing evidence, and chronology inconsistencies earlier in the workflow.

## Author And Status

- Author: Manav Joshi
- Status: Final submission polish complete and repository prepared for hackathon evaluation
