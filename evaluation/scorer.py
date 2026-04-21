"""Hackathon-aligned scoring."""

from __future__ import annotations

from evaluation.metrics import f1_score


def score_submission(module_scores: dict[str, dict[str, int]]) -> dict[str, float]:
    """Compute per-module and overall hackathon score."""
    summary: dict[str, float] = {}
    per_module = []
    for module_name, counts in module_scores.items():
        score = f1_score(counts.get("tp", 0), counts.get("fp", 0), counts.get("fn", 0))
        summary[module_name] = round(score, 4)
        per_module.append(score)
    summary["overall"] = round(sum(per_module) / len(per_module), 4) if per_module else 0.0
    return summary


def score_hackathon_components(classification: float, rules: float, design: float) -> dict[str, float | str]:
    """Simulate official weighted scoring and identify the main bottleneck."""
    weighted = 0.4 * classification + 0.4 * rules + 0.2 * design
    components = {
        "classification": round(classification, 4),
        "rules": round(rules, 4),
        "design": round(design, 4),
    }
    weakest = min(components.items(), key=lambda item: item[1])[0]
    return {
        "classification": components["classification"],
        "rules": components["rules"],
        "design": components["design"],
        "overall": round(weighted, 4),
        "primary_score_reducer": weakest,
    }
