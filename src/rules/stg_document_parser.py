"""Parse real STG documents into structured rule profiles."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path


@dataclass
class ParsedSTGDocument:
    """Intermediate parsed STG artifact."""

    source_path: str
    package_name: str
    sections: dict[str, str]
    required_documents: list[str]
    clinical_rules: list[dict]
    investigations: list[str]
    match: dict
    claim_types: list[str]


class STGDocumentParser:
    """Best-effort parser for text and PDF STG documents."""

    SECTION_ALIASES = {
        "package_name": ["package", "package name", "procedure", "surgical package", "medical package"],
        "mandatory_documents": ["mandatory documents", "required documents", "documents required", "claim documents"],
        "clinical_conditions": ["clinical conditions", "eligibility", "indications", "clinical criteria", "conditions"],
        "investigations": ["investigations", "required investigations", "diagnostic tests", "preoperative investigations"],
        "thresholds": ["thresholds", "criteria", "laboratory criteria", "clinical thresholds"],
    }

    DOCUMENT_LABELS = {
        "claim form": "claim_form",
        "preauth": "claim_form",
        "pre authorization": "claim_form",
        "discharge summary": "discharge_summary",
        "summary": "discharge_summary",
        "procedure note": "procedure_note",
        "operation note": "procedure_note",
        "surgery note": "procedure_note",
        "bill": "bill",
        "invoice": "bill",
        "final bill": "bill",
    }

    CLINICAL_FIELD_PATTERNS = [
        ("hemoglobin", r"(?:hemoglobin|haemoglobin|hb)\s*(>=|<=|>|<|=)\s*(\d+(?:\.\d+)?)"),
        ("fever_duration_days", r"(?:fever duration|duration of fever|fever)\s*(>=|<=|>|<|=)\s*(\d+(?:\.\d+)?)\s*day"),
    ]

    INVESTIGATION_KEYWORDS = {
        "x-ray": ["x-ray", "xray"],
        "ct": ["ct", "ct scan"],
        "mri": ["mri"],
        "ultrasound": ["ultrasound", "usg"],
        "blood test": ["cbc", "blood test", "hemoglobin", "haemoglobin"],
    }

    def parse_sources(self, items: list[str | dict]) -> list[dict]:
        """Parse configured STG sources into normalized profiles."""
        profiles: list[dict] = []
        for item in items:
            if isinstance(item, dict):
                path_value = item.get("path", "")
                claim_types = item.get("claim_types", [])
            else:
                path_value = str(item)
                claim_types = []
            if not path_value:
                continue
            parsed = self.parse_path(path_value, claim_types=claim_types)
            if parsed is not None:
                profiles.append(self._to_profile(parsed))
        return profiles

    def parse_path(self, path_value: str, claim_types: list[str] | None = None) -> ParsedSTGDocument | None:
        """Parse a single STG document path."""
        path = Path(path_value)
        if not path.exists():
            return None
        text = self._extract_text(path)
        if not text.strip():
            return None
        sections = self._split_sections(text)
        package_name = self._package_name(path, text, sections)
        required_documents = self._required_documents(sections)
        clinical_rules = self._clinical_rules(sections)
        investigations = self._investigations(sections)
        match = self._match_hints(package_name, sections)
        return ParsedSTGDocument(
            source_path=str(path),
            package_name=package_name,
            sections=sections,
            required_documents=required_documents,
            clinical_rules=clinical_rules,
            investigations=investigations,
            match=match,
            claim_types=claim_types or self._claim_types_from_text(text),
        )

    def _extract_text(self, path: Path) -> str:
        if path.suffix.lower() in {".txt", ".md"}:
            return path.read_text(encoding="utf-8", errors="ignore")
        if path.suffix.lower() == ".pdf":
            sidecar = path.with_suffix(".txt")
            if sidecar.exists():
                return sidecar.read_text(encoding="utf-8", errors="ignore")
            return self._extract_pdf_text(path)
        return path.read_text(encoding="utf-8", errors="ignore")

    @staticmethod
    def _extract_pdf_text(path: Path) -> str:
        """Use lightweight PDF text recovery without adding architecture dependencies."""
        data = path.read_bytes()
        decoded = data.decode("latin-1", errors="ignore")
        chunks = re.findall(r"\(([^\)]{3,200})\)", decoded)
        if chunks:
            return "\n".join(chunk for chunk in chunks if any(char.isalpha() for char in chunk))
        fallback = re.sub(r"[^A-Za-z0-9:\-_/.,()\n ]+", " ", decoded)
        return re.sub(r"\s{2,}", " ", fallback)

    def _split_sections(self, text: str) -> dict[str, str]:
        normalized = text.replace("\r", "\n")
        lines = [line.strip() for line in normalized.splitlines()]
        sections: dict[str, list[str]] = {}
        current = "body"
        sections[current] = []
        for line in lines:
            if not line:
                continue
            section_key = self._closest_section(line)
            if section_key:
                current = section_key
                sections.setdefault(current, [])
                remainder = self._section_remainder(line)
                if remainder:
                    sections[current].append(remainder)
                continue
            sections.setdefault(current, []).append(line)
        return {key: "\n".join(value).strip() for key, value in sections.items() if value}

    def _closest_section(self, line: str) -> str | None:
        lowered = line.lower().strip(" :-")
        for section_key, aliases in self.SECTION_ALIASES.items():
            for alias in aliases:
                if lowered.startswith(alias):
                    return section_key
        best_key: str | None = None
        best_score = 0.0
        for section_key, aliases in self.SECTION_ALIASES.items():
            for alias in aliases:
                score = SequenceMatcher(None, lowered[: len(alias) + 10], alias).ratio()
                if score > best_score:
                    best_key = section_key
                    best_score = score
        return best_key if best_score >= 0.78 else None

    @staticmethod
    def _section_remainder(line: str) -> str:
        parts = re.split(r"[:\-]", line, maxsplit=1)
        return parts[1].strip() if len(parts) > 1 else ""

    def _package_name(self, path: Path, text: str, sections: dict[str, str]) -> str:
        value = sections.get("package_name", "")
        if value:
            first_line = value.splitlines()[0].strip()
            if len(first_line) >= 3:
                return first_line.title()
        first_text_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
        if "package" in first_text_line.lower():
            return re.sub(r"(?i)^package\s*[:\-]?\s*", "", first_text_line).strip().title()
        return path.stem.replace("_", " ").replace("-", " ").title()

    def _required_documents(self, sections: dict[str, str]) -> list[str]:
        text = "\n".join(
            value for key, value in sections.items() if key in {"mandatory_documents", "body"}
        ).lower()
        found: list[str] = []
        for phrase, label in self.DOCUMENT_LABELS.items():
            if phrase in text and label not in found:
                found.append(label)
        return found

    def _clinical_rules(self, sections: dict[str, str]) -> list[dict]:
        text = "\n".join(
            value for key, value in sections.items() if key in {"clinical_conditions", "thresholds", "body"}
        ).lower()
        rules: list[dict] = []
        for field_name, pattern in self.CLINICAL_FIELD_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                operator_value = match.group(1).replace("=", "==") if match.group(1) == "=" else match.group(1)
                rules.append(
                    {
                        "rule_id": f"{field_name}_{match.start()}",
                        "field": field_name,
                        "operator": operator_value,
                        "value": float(match.group(2)) if "." in match.group(2) else int(match.group(2)),
                        "severity": "high",
                        "required": False,
                        "message": f"STG threshold failed for '{field_name}'.",
                        "source": "stg_document",
                    }
                )
        for investigation in self._investigations(sections):
            rules.append(
                {
                    "rule_id": f"investigation_{investigation.replace(' ', '_')}",
                    "field": "imaging_findings" if investigation in {"x-ray", "ct", "mri", "ultrasound"} else "hemoglobin",
                    "contains_any": [investigation],
                    "severity": "medium",
                    "required": False,
                    "message": f"Required investigation '{investigation}' not supported by extracted evidence.",
                    "source": "stg_document",
                }
            )
        return self._dedupe_rules(rules)

    def _investigations(self, sections: dict[str, str]) -> list[str]:
        text = "\n".join(
            value for key, value in sections.items() if key in {"investigations", "clinical_conditions", "body"}
        ).lower()
        found: list[str] = []
        for normalized_name, aliases in self.INVESTIGATION_KEYWORDS.items():
            if any(re.search(rf"\b{re.escape(alias)}\b", text) for alias in aliases):
                found.append(normalized_name)
        return found

    def _match_hints(self, package_name: str, sections: dict[str, str]) -> dict:
        body = "\n".join(sections.values()).lower()
        diagnosis_terms = self._extract_inline_terms(body, "diagnosis")
        procedure_terms = self._extract_inline_terms(body, "procedure")
        package_terms = self._important_tokens(package_name)
        return {
            "diagnosis_any": diagnosis_terms,
            "procedure_any": procedure_terms,
            "package_any": package_terms,
        }

    @staticmethod
    def _extract_inline_terms(text: str, label: str) -> list[str]:
        patterns = [
            rf"{label}\s*[:\-]\s*([a-z0-9 ,/()-]+)",
            rf"{label}\s+(?:include|includes|such as)\s+([a-z0-9 ,/()-]+)",
        ]
        terms: list[str] = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                terms.extend(STGDocumentParser._split_terms(match.group(1)))
        return STGDocumentParser._dedupe_terms(terms)

    @staticmethod
    def _important_tokens(text: str) -> list[str]:
        tokens = [token.lower() for token in re.split(r"[^a-z0-9]+", text) if len(token) >= 4]
        return STGDocumentParser._dedupe_terms(tokens)

    @staticmethod
    def _split_terms(value: str) -> list[str]:
        return [item.strip().lower() for item in re.split(r"[,;/]| and ", value) if item.strip()]

    @staticmethod
    def _dedupe_terms(values: list[str]) -> list[str]:
        seen: list[str] = []
        for value in values:
            if value and value not in seen:
                seen.append(value)
        return seen

    @staticmethod
    def _dedupe_rules(rules: list[dict]) -> list[dict]:
        best: dict[tuple[str, str], dict] = {}
        for rule in rules:
            key = (rule.get("field", ""), rule.get("rule_id", ""))
            best[key] = rule
        return list(best.values())

    @staticmethod
    def _claim_types_from_text(text: str) -> list[str]:
        lowered = text.lower()
        claim_types: list[str] = []
        if any(token in lowered for token in ("surgery", "procedure", "operation")):
            claim_types.append("surgery_claim")
        if any(token in lowered for token in ("medical management", "medical package", "medicine")):
            claim_types.append("medical_claim")
        return claim_types

    def _to_profile(self, parsed: ParsedSTGDocument) -> dict:
        package_id = re.sub(r"[^a-z0-9]+", "_", parsed.package_name.lower()).strip("_")
        return {
            "package_id": package_id,
            "package_name": parsed.package_name,
            "claim_types": parsed.claim_types,
            "required_documents": parsed.required_documents,
            "clinical_rules": parsed.clinical_rules,
            "required_investigations": parsed.investigations,
            "match": parsed.match,
            "source_document": parsed.source_path,
            "source_type": "stg_document",
            "document_rules": [],
            "fraud_rules": [],
        }
