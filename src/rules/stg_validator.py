"""Clinical alignment validators."""

from __future__ import annotations

from src.core.state_manager import FieldCandidate, RuleViolation


class STGValidator:
    """Validate diagnosis and procedure alignment."""

    def validate(self, fields: dict[str, list[FieldCandidate]], profile: dict) -> tuple[list[RuleViolation], list[dict]]:
        """Check if extracted procedures and diagnoses align with the selected STG profile."""
        diagnoses = {str(item.value).lower() for item in fields.get("diagnosis", [])}
        procedures = {str(item.value).lower() for item in fields.get("procedure", [])}
        match = profile.get("match", {})
        allowed_diagnoses = match.get("diagnosis_any", [])
        allowed_procedures = match.get("procedure_any", [])
        violations: list[RuleViolation] = []
        summaries: list[dict] = []
        if allowed_diagnoses:
            diagnosis_pass = any(any(token in diagnosis for token in allowed_diagnoses) for diagnosis in diagnoses)
            summaries.append(
                {
                    "rule_id": "diagnosis_alignment",
                    "status": "pass" if diagnosis_pass else "fail",
                    "observed": sorted(diagnoses),
                    "expected": allowed_diagnoses,
                }
            )
            if not diagnosis_pass and diagnoses:
                violations.append(
                    RuleViolation(
                        rule_name="diagnosis_alignment",
                        severity="high",
                        message=f"Diagnosis does not align with selected STG package '{profile.get('package_name')}'.",
                        evidence=[{"diagnoses": sorted(diagnoses), "expected": allowed_diagnoses}],
                    )
                )
        if allowed_procedures:
            procedure_pass = any(any(token in procedure for token in allowed_procedures) for procedure in procedures)
            summaries.append(
                {
                    "rule_id": "procedure_alignment",
                    "status": "pass" if procedure_pass else "fail",
                    "observed": sorted(procedures),
                    "expected": allowed_procedures,
                }
            )
            if not procedure_pass and procedures:
                violations.append(
                    RuleViolation(
                        rule_name="procedure_alignment",
                        severity="high",
                        message=f"Procedure does not align with selected STG package '{profile.get('package_name')}'.",
                        evidence=[{"procedures": sorted(procedures), "expected": allowed_procedures}],
                    )
                )
        return violations, summaries
