"""Explainability report generation."""

from __future__ import annotations

from src.core.state_manager import DecisionResult, ProcessingState


class ExplainabilityReportGenerator:
    """Generate a final explainability payload."""

    def generate(self, state: ProcessingState, decision: DecisionResult, trace: dict) -> dict:
        """Return a structured report artifact."""
        module_confidences = {
            "ocr": round(sum(item.confidence for item in state.ocr_results) / len(state.ocr_results), 4)
            if state.ocr_results
            else 0.0,
            "classification": round(
                sum(item.confidence for item in state.classification_results) / len(state.classification_results), 4
            )
            if state.classification_results
            else 0.0,
            "timeline": round(sum(item.confidence for item in state.timeline) / len(state.timeline), 4)
            if state.timeline
            else 0.0,
        }
        return {
            "claim_id": state.claim_id,
            "summary": {
                "status": decision.status,
                "confidence": decision.confidence,
                "reasons": decision.reasons,
            },
            "module_confidences": module_confidences,
            "trace": trace,
            "documents": state.documents,
            "rule_results": state.debug.get("rule_evaluation", {}),
            "debug": state.debug,
            "evidence_overview": {
                "field_evidence_count": sum(len(items) for items in trace.get("fields", {}).values()),
                "visual_evidence_count": len(trace.get("visual_detections", [])),
                "violation_count": len(trace.get("violations", [])),
            },
        }
