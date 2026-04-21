"""STG package loading and profile selection."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from src.core.state_manager import FieldCandidate
from src.rules.stg_document_parser import STGDocumentParser


class STGProfileLoader:
    """Load procedure-agnostic STG profiles from structured config or text artifacts."""

    def __init__(self) -> None:
        self.document_parser = STGDocumentParser()

    def load(self, rules: dict) -> list[dict]:
        document_profiles = self._parse_text_documents(rules.get("stg_documents", []))
        profiles = [self._normalize_profile(item) for item in rules.get("stg_packages", [])]
        return document_profiles + profiles

    def select_profile(self, rules: dict, claim_type: str, fields: dict[str, list[FieldCandidate]]) -> dict:
        profiles = self.load(rules)
        evidence = self._field_values(fields)
        best_profile: dict | None = None
        best_score = -1.0
        for profile in profiles:
            claim_types = profile.get("claim_types", [])
            if claim_types and claim_type not in claim_types:
                continue
            score = self._match_score(profile, evidence)
            if score > best_score:
                best_profile = profile
                best_score = score
        if best_profile is not None and best_score > 0:
            best_profile["selection_score"] = best_score
            return best_profile

        required_documents = rules.get("required_documents", {}).get(claim_type, [])
        return {
            "package_id": claim_type,
            "package_name": claim_type.replace("_", " ").title(),
            "claim_types": [claim_type],
            "required_documents": required_documents,
            "clinical_rules": [],
            "document_rules": [],
            "fraud_rules": [],
            "selection_score": 0.0,
            "match": {},
        }

    def _match_score(self, profile: dict, evidence: dict[str, set[str]]) -> float:
        match = profile.get("match", {})
        score = 0.0
        for field_name, weight in (("diagnosis", 2.5), ("procedure", 2.5)):
            terms = match.get(f"{field_name}_any", [])
            values = evidence.get(field_name, set())
            score += weight * self._best_term_match(terms, values)
        package_terms = match.get("package_any", [])
        package_values = evidence.get("claim_package", set()) | evidence.get("claim_id", set()) | evidence.get("diagnosis", set()) | evidence.get("procedure", set())
        score += 1.5 * self._best_term_match(package_terms, package_values)
        investigation_terms = profile.get("required_investigations", [])
        score += 0.75 * self._best_term_match(investigation_terms, evidence.get("imaging_findings", set()))
        if profile.get("source_type") == "stg_document":
            score += 0.15
        return score

    def _parse_text_documents(self, documents: list[str | dict]) -> list[dict]:
        return [self._normalize_profile(item) for item in self.document_parser.parse_sources(documents)]

    @staticmethod
    def _split_terms(value: str) -> list[str]:
        return [item.strip().lower() for item in re.split(r"[,;/]", value) if item.strip()]

    @staticmethod
    def _field_values(fields: dict[str, list[FieldCandidate]]) -> dict[str, set[str]]:
        return {
            field_name: {str(item.value).lower() for item in items}
            for field_name, items in fields.items()
        }

    @staticmethod
    def _normalize_profile(profile: dict) -> dict:
        normalized = dict(profile)
        normalized.setdefault("package_id", normalized.get("package_name", "default"))
        normalized.setdefault("package_name", normalized["package_id"])
        normalized.setdefault("claim_types", [])
        normalized.setdefault("match", {})
        normalized.setdefault("required_documents", [])
        normalized.setdefault("clinical_rules", [])
        normalized.setdefault("required_investigations", [])
        normalized.setdefault("document_rules", [])
        normalized.setdefault("fraud_rules", [])
        normalized.setdefault("source_type", "config")
        return normalized

    @staticmethod
    def _best_term_match(terms: list[str], values: set[str]) -> float:
        if not terms or not values:
            return 0.0
        best = 0.0
        for term in terms:
            for value in values:
                if term in value or value in term:
                    best = max(best, 1.0)
                    continue
                best = max(best, SequenceMatcher(None, term, value).ratio())
        return best if best >= 0.74 else 0.0
