"""Shared dataclasses and state containers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


BBox = tuple[int, int, int, int]


@dataclass
class OCRWord:
    """Single OCR token with metadata."""

    text: str
    confidence: float
    bbox: BBox
    source: str


@dataclass
class OCRPageResult:
    """OCR output for a single page."""

    page_number: int
    full_text: str
    words: list[OCRWord]
    confidence: float
    source: str
    image_path: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClassificationResult:
    """Predicted page-level document class."""

    page_number: int
    label: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FieldCandidate:
    """Extracted structured field with provenance."""

    field_name: str
    value: Any
    confidence: float
    page_number: int
    bbox: BBox
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VisualDetection:
    """Visual object detection result."""

    page_number: int
    label: str
    confidence: float
    bbox: BBox
    source: str


@dataclass
class TimelineEvent:
    """Temporal event in the claim journey."""

    event_type: str
    date: str
    page_number: int
    confidence: float
    evidence: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleViolation:
    """Business rule violation."""

    rule_name: str
    severity: str
    message: str
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class DecisionResult:
    """Final adjudication output."""

    status: str
    confidence: float
    reasons: list[str]
    evidence: list[dict[str, Any]]


@dataclass
class DocumentPage:
    """Normalized page artifact."""

    claim_id: str
    source_document: str
    page_number: int
    image_path: str
    file_path: str


@dataclass
class ProcessingState:
    """Mutable processing state for a claim."""

    claim_id: str
    documents: list[dict[str, Any]] = field(default_factory=list)
    pages: list[DocumentPage] = field(default_factory=list)
    ocr_results: list[OCRPageResult] = field(default_factory=list)
    classification_results: list[ClassificationResult] = field(default_factory=list)
    extracted_fields: dict[str, list[FieldCandidate]] = field(default_factory=dict)
    visual_detections: list[VisualDetection] = field(default_factory=list)
    timeline: list[TimelineEvent] = field(default_factory=list)
    rule_violations: list[RuleViolation] = field(default_factory=list)
    decision: DecisionResult | None = None
    debug: dict[str, Any] = field(default_factory=dict)

    def add_field(self, candidate: FieldCandidate) -> None:
        """Append a field candidate under its field name."""
        self.extracted_fields.setdefault(candidate.field_name, []).append(candidate)

    def register_document(self, file_path: str | Path) -> None:
        """Track an input document."""
        path = Path(file_path)
        self.documents.append(
            {
                "name": path.name,
                "path": str(path),
                "suffix": path.suffix.lower(),
            }
        )
