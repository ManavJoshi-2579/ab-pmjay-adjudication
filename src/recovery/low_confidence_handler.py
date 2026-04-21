"""Low-confidence handling policies."""

from __future__ import annotations

from src.core.state_manager import DecisionResult


class LowConfidenceHandler:
    """Downgrade low-confidence passes to conditional outcomes."""

    def apply(self, decision: DecisionResult, threshold: float = 0.65) -> DecisionResult:
        """Adjust status for uncertain claims."""
        if decision.confidence < threshold and decision.status == "Pass":
            decision.status = "Conditional"
            decision.reasons.append("Decision confidence below review threshold.")
        return decision
