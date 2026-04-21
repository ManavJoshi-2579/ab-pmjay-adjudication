"""Optimization, self-evaluation, and scoring diagnostics."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from src.core.state_manager import ProcessingState
from src.utils.io import load_json


class PipelineOptimizer:
    """Analyze run quality, detect weak points, and simulate scoring impact."""

    CORE_FIELDS = ("patient_name", "diagnosis", "procedure", "dates", "amounts")

    def __init__(self, thresholds: dict) -> None:
        self.thresholds = thresholds

    def self_evaluate(self, state: ProcessingState) -> dict[str, Any]:
        """Compute internal metrics and identify weak components."""
        classification_confidences = [item.confidence for item in state.classification_results]
        rule_counter = Counter(item.rule_name for item in state.rule_violations)
        extraction_presence = {field: bool(state.extracted_fields.get(field)) for field in self.CORE_FIELDS}
        extraction_completeness = sum(extraction_presence.values()) / len(self.CORE_FIELDS)
        weak_components: list[dict[str, Any]] = []

        classification_threshold = self.thresholds.get("classification", {}).get("low_confidence_threshold", 0.68)
        if classification_confidences and mean(classification_confidences) < classification_threshold:
            weak_components.append(
                {
                    "component": "classification",
                    "reason": "Mean classification confidence below optimization threshold.",
                    "mean_confidence": round(mean(classification_confidences), 4),
                }
            )
        extraction_threshold = self.thresholds.get("extraction", {}).get("completeness_threshold", 0.8)
        if extraction_completeness < extraction_threshold:
            weak_components.append(
                {
                    "component": "extraction",
                    "reason": "Extraction completeness below target.",
                    "completeness": round(extraction_completeness, 4),
                }
            )
        if state.rule_violations:
            weak_components.append(
                {
                    "component": "rules",
                    "reason": "Rule violations present in final decision.",
                    "top_violations": rule_counter.most_common(3),
                }
            )
        adaptive_actions = self._adaptive_actions(state, weak_components)

        return {
            "classification_confidence_distribution": self._distribution(classification_confidences),
            "rule_violation_frequency": dict(rule_counter),
            "extraction_completeness": {
                "coverage": round(extraction_completeness, 4),
                "fields_present": extraction_presence,
            },
            "weak_components": weak_components,
            "adaptive_actions": adaptive_actions,
        }

    def error_analysis(self, state: ProcessingState) -> dict[str, Any]:
        """Detect confidence, conflict, and missing-data issues."""
        issues: list[dict[str, Any]] = []
        class_threshold = self.thresholds.get("classification", {}).get("low_confidence_threshold", 0.68)
        for item in state.classification_results:
            if item.confidence < class_threshold:
                issues.append(
                    {
                        "type": "low_confidence_prediction",
                        "page_number": item.page_number,
                        "label": item.label,
                        "confidence": item.confidence,
                    }
                )
            votes = item.metadata.get("votes", [])
            labels = {vote["label"] for vote in votes}
            if len(labels) > 1:
                issues.append(
                    {
                        "type": "conflicting_classification_votes",
                        "page_number": item.page_number,
                        "votes": votes,
                    }
                )
        for field_name in self.CORE_FIELDS:
            if not state.extracted_fields.get(field_name):
                issues.append({"type": "missing_field", "field_name": field_name})
        for violation in state.rule_violations:
            if violation.severity in {"high", "medium"}:
                issues.append(
                    {
                        "type": "rule_issue",
                        "rule_name": violation.rule_name,
                        "severity": violation.severity,
                        "message": violation.message,
                    }
                )
        return {"issues": issues, "issue_count": len(issues)}

    def hackathon_score(self, state: ProcessingState) -> dict[str, Any]:
        """Simulate weighted hackathon scoring and identify largest drag."""
        weights = self.thresholds.get("optimization", {}).get(
            "score_weights",
            {"classification": 0.4, "rules": 0.4, "design": 0.2},
        )
        classification_score = (
            mean(item.confidence for item in state.classification_results) if state.classification_results else 0.0
        )
        rule_penalty = sum(0.2 if item.severity == "high" else 0.1 for item in state.rule_violations)
        rules_score = max(0.0, min(1.0, 1.0 - rule_penalty))
        design_score = self._design_score(state)
        components = {
            "classification": round(classification_score, 4),
            "rules": round(rules_score, 4),
            "design": round(design_score, 4),
        }
        weighted_score = sum(components[name] * weights.get(name, 0.0) for name in components)
        weakest_component = min(components.items(), key=lambda item: item[1])[0]
        return {
            "components": components,
            "weights": weights,
            "weighted_score": round(weighted_score, 4),
            "primary_score_reducer": weakest_component,
        }

    def edge_case_simulation(self) -> dict[str, Any]:
        """Return built-in edge-case scenarios for evaluation."""
        scenarios = [
            {"name": "missing_fields", "expected_behavior": "regex fallback and conditional/fail downgrade"},
            {"name": "wrong_sequence", "expected_behavior": "temporal rule violation detected"},
            {"name": "extra_documents", "expected_behavior": "ignore extras without harming required-doc checks"},
        ]
        return {"enabled": True, "scenarios": scenarios}

    def history_analysis(self, debug_dir: str | Path, limit: int = 10) -> dict[str, Any]:
        """Analyze recent debug artifacts to surface repeated failure patterns."""
        root = Path(debug_dir)
        if not root.exists():
            return {"runs_analyzed": 0, "common_issues": [], "recommended_focus": []}
        files = sorted(root.glob("*_debug.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:limit]
        issue_counter: Counter[str] = Counter()
        weak_counter: Counter[str] = Counter()
        for file in files:
            payload = load_json(file)
            for issue in payload.get("error_analysis", {}).get("issues", []):
                issue_counter[issue.get("type", "unknown")] += 1
            for component in payload.get("self_evaluation", {}).get("weak_components", []):
                weak_counter[component.get("component", "unknown")] += 1
        focus = [component for component, _ in weak_counter.most_common(3)]
        return {
            "runs_analyzed": len(files),
            "common_issues": issue_counter.most_common(5),
            "recommended_focus": focus,
        }

    def _adaptive_actions(self, state: ProcessingState, weak_components: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Suggest automatic threshold and fallback adjustments from current errors."""
        actions: list[dict[str, Any]] = []
        low_conf_count = sum(
            1 for item in state.classification_results
            if item.confidence < self.thresholds.get("classification", {}).get("low_confidence_threshold", 0.68)
        )
        if low_conf_count >= max(1, len(state.classification_results) // 2):
            actions.append(
                {
                    "component": "classification",
                    "suggestion": "Lower cnn weight and increase keyword/layout-aware class weights.",
                }
            )
        if any(component["component"] == "extraction" for component in weak_components):
            actions.append(
                {
                    "component": "extraction",
                    "suggestion": "Tighten regex fallback activation and lower completeness threshold for noisy pages.",
                }
            )
        if any(item.rule_name == "missing_timeline_events" for item in state.rule_violations):
            actions.append(
                {
                    "component": "timeline",
                    "suggestion": "Increase event-specific keyword detection and preserve same-day ordering hints.",
                }
            )
        return actions

    @staticmethod
    def _distribution(values: list[float]) -> dict[str, float]:
        """Summarize a confidence distribution."""
        if not values:
            return {"min": 0.0, "max": 0.0, "mean": 0.0}
        return {"min": round(min(values), 4), "max": round(max(values), 4), "mean": round(mean(values), 4)}

    def _design_score(self, state: ProcessingState) -> float:
        """Estimate design quality from explainability and recoverability coverage."""
        evidence_count = len(state.decision.evidence) if state.decision else 0
        provenance_score = 1.0 if evidence_count else 0.5
        recovery_score = 1.0 if any(item.metadata.get("recovered_from") for item in state.ocr_results) or state.debug else 0.7
        explainability_score = 1.0 if all("path" in item for item in state.documents) else 0.7
        return round((provenance_score + recovery_score + explainability_score) / 3, 4)
