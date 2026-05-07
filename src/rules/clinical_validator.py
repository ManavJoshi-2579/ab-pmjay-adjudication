"""Generic STG-driven clinical rule validation."""

from __future__ import annotations

import operator

from src.core.state_manager import FieldCandidate, RuleViolation


class ClinicalRuleValidator:
    """Apply generic clinical comparisons loaded from STG profiles."""

    OPERATORS = {
        ">=": operator.ge,
        ">": operator.gt,
        "<=": operator.le,
        "<": operator.lt,
        "==": operator.eq,
    }

    def validate(self, fields: dict[str, list[FieldCandidate]], profile: dict) -> tuple[list[RuleViolation], list[dict]]:
        violations: list[RuleViolation] = []
        summaries: list[dict] = []
        for rule in profile.get("clinical_rules", []):
            field_name = rule.get("field")
            candidates = fields.get(field_name, [])
            summary = {
                "rule_id": rule.get("rule_id", field_name),
                "field": field_name,
                "status": "pass",
                "message": rule.get("message", ""),
                "observed": [item.value for item in candidates],
            }
            if not candidates:
                if rule.get("required", False):
                    severity = rule.get("missing_severity", rule.get("severity", "medium"))
                    violations.append(
                        RuleViolation(
                            rule_name=summary["rule_id"],
                            severity=severity,
                            message=rule.get("missing_message", f"Required clinical field '{field_name}' missing."),
                            evidence=[{"field": field_name}],
                        )
                    )
                    summary["status"] = "fail"
                else:
                    summary["status"] = "not_applicable"
                summaries.append(summary)
                continue

            if "operator" in rule:
                if not self._numeric_rule_passes(candidates, rule):
                    violations.append(
                        RuleViolation(
                            rule_name=summary["rule_id"],
                            severity=rule.get("severity", "high"),
                            message=rule.get("message", f"Clinical threshold failed for '{field_name}'."),
                            evidence=[{"field": field_name, "observed": [item.value for item in candidates], "rule": rule}],
                        )
                    )
                    summary["status"] = "fail"
            elif "contains_any" in rule:
                if not self._contains_rule_passes(candidates, rule.get("contains_any", [])):
                    violations.append(
                        RuleViolation(
                            rule_name=summary["rule_id"],
                            severity=rule.get("severity", "medium"),
                            message=rule.get("message", f"Clinical evidence failed for '{field_name}'."),
                            evidence=[{"field": field_name, "observed": [item.value for item in candidates], "rule": rule}],
                        )
                    )
                    summary["status"] = "fail"
            summaries.append(summary)
        return violations, summaries

    def _numeric_rule_passes(self, candidates: list[FieldCandidate], rule: dict) -> bool:
        compare = self.OPERATORS.get(rule.get("operator", "=="))
        if compare is None:
            return True
        threshold = float(rule.get("value", 0))
        return any(compare(float(item.value), threshold) for item in candidates)

    @staticmethod
    def _contains_rule_passes(candidates: list[FieldCandidate], terms: list[str]) -> bool:
        lowered_terms = [term.lower() for term in terms]
        for item in candidates:
            value = str(item.value).lower()
            if any(term in value for term in lowered_terms):
                return True
        return False
