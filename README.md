# NHA STG-Based Adjudication System

A production-ready, explainable claim adjudication system for PMJAY-style healthcare workflows. The project evaluates multi-document claim packets against Standard Treatment Guidelines (STGs), reconstructs claim timelines, validates supporting evidence, and produces deterministic pass/fail decisions with traceable reasons.

## Overview

This repository is designed for evaluation and demo readiness. It combines configurable rules, STG-aware validation, document parsing, OCR adapters, and explainability outputs into a single adjudication pipeline that can be run locally with `main.py` or exposed through the API layer.

## Core Features

- STG-driven adjudication using configurable rules and discovered STG documents.
- Procedure-agnostic pipeline that operates across varied claim types and document mixes.
- Explainable decisions with evidence traces, debug artifacts, and reasoned outcomes.
- Modular architecture covering OCR, extraction, classification, rules, timeline, recovery, and decisioning.
- Safe local execution with deterministic fallbacks when heavyweight ML dependencies are unavailable.

## Architecture

The project is organized into focused modules:

- `src/core/`: pipeline orchestration and claim processing flow.
- `src/ocr/`: OCR backends and ensemble wrappers.
- `src/classification/`, `src/extraction/`, `src/timeline/`: document understanding and temporal reconstruction.
- `src/rules/`: STG loading, document validation, anomaly detection, and clinical checks.
- `src/decision/`: confidence scoring and final adjudication.
- `src/explainability/`: evidence tracing and report generation.
- `api/`: FastAPI serving layer for programmatic access.
- `configs/`: YAML/JSON configuration, thresholds, and rule definitions.
- `scripts/`: pipeline utilities, training helpers, and synthetic-data generation.
- `data/`: local input, synthetic, and STG source material.

## How To Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the adjudication pipeline:

```bash
python -B main.py
```

Run the helper pipeline script:

```bash
python scripts/run_pipeline.py --input-dir data/input
```

Run tests:

```bash
pytest
```

Run the API locally:

```bash
uvicorn api.app:app --reload
```

## Processing Flow

1. Claim documents are loaded from the configured input directories.
2. OCR and document parsing extract structured evidence from the packet.
3. Timeline reconstruction and rule validation check consistency and medical flow.
4. STG and document checks evaluate claim sufficiency and procedural alignment.
5. The decision engine emits an explainable adjudication with confidence and reasons.

## Output Format

Typical outputs include a final decision payload, debug details, and evidence text files. A representative decision object looks like:

```json
{
  "claim_id": "example-claim",
  "documents": [],
  "timeline": [],
  "decision": {
    "status": "Pass",
    "confidence": 0.0,
    "reasons": [],
    "evidence": []
  }
}
```

## Reproducibility Notes

- Generated outputs, logs, caches, and local environment files are excluded from version control.
- The repository is structured so the project can be cloned and run locally with standard Python tooling.
- Heuristic wrappers can be replaced with production OCR and model integrations without changing the orchestration contract.
