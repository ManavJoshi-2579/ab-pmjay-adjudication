"""Strict payload schema validator for evaluation outputs."""

from __future__ import annotations


class PayloadSchemaValidator:
    """Validate the pipeline payload shape before returning it."""

    REQUIRED_TOP_LEVEL = {
        "claim_id",
        "documents",
        "page_outputs",
        "summary",
        "decision",
        "reasoning",
        "extracted_fields",
        "extracted_field_details",
        "rule_results",
        "timeline",
        "explainability",
        "optimization",
    }

    REQUIRED_DECISION = {
        "status",
        "confidence",
        "reasons",
        "reason_count",
        "summary_explanation",
        "confidence_explanation",
        "key_evidence",
        "reasoning_path",
        "evidence",
    }

    def validate(self, payload: dict) -> dict:
        missing = sorted(self.REQUIRED_TOP_LEVEL - set(payload))
        decision_missing = sorted(self.REQUIRED_DECISION - set(payload.get("decision", {})))
        return {
            "valid": not missing and not decision_missing,
            "missing_top_level": missing,
            "missing_decision_keys": decision_missing,
        }
