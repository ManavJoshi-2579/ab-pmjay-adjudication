"""Dependency assembly."""

from __future__ import annotations

from src.classification.ensemble import ClassificationEnsemble
from src.core.optimizer import PipelineOptimizer
from src.decision.decision_engine import DecisionEngine
from src.explainability.provenance import ProvenanceBuilder
from src.explainability.report_generator import ExplainabilityReportGenerator
from src.explainability.trace_builder import TraceBuilder
from src.extraction.fusion import ExtractionFusion
from src.ocr.ensemble import OCREnsemble
from src.recovery.fallback_logic import FallbackLogic
from src.recovery.low_confidence_handler import LowConfidenceHandler
from src.recovery.ocr_retry import OCRRetryHandler
from src.rules.engine import RuleEngine
from src.timeline.date_extractor import DateExtractor
from src.timeline.sequence_builder import SequenceBuilder
from src.vision.postprocess import VisionPostProcessor
from src.vision.validator import VisionValidator
from src.vision.yolo import YOLODetector


class PipelineOrchestrator:
    """Factory for all pipeline dependencies."""

    def __init__(self, config: dict, thresholds: dict, rules: dict) -> None:
        self.config = config
        self.thresholds = thresholds
        self.rules = rules
        self.ocr = OCREnsemble(
            cache_dir=config.get("pipeline", {}).get("cache", {}).get("ocr_dir"),
            weights=config.get("pipeline", {}).get("ocr", {}).get("weights", {}),
            agreement_boost=thresholds.get("ocr", {}).get("agreement_boost", 0.08),
            disagreement_penalty=thresholds.get("ocr", {}).get("disagreement_penalty", 0.08),
        )
        self.ocr_retry = OCRRetryHandler()
        self.classifier = ClassificationEnsemble(
            weights=config.get("pipeline", {}).get("classification", {}).get("weights", {}),
            keyword_override_gap=thresholds.get("classification", {}).get("keyword_override_gap", 0.12),
            class_weights=config.get("pipeline", {}).get("classification", {}).get("class_weights", {}),
            keyword_boosts=config.get("pipeline", {}).get("classification", {}).get("keyword_boosts", {}),
            rerank_margin=thresholds.get("classification", {}).get("rerank_margin", 0.18),
            hard_overrides=config.get("pipeline", {}).get("classification", {}).get("hard_overrides", {}),
            class_thresholds=thresholds.get("classification", {}).get("class_thresholds", {}),
            context_correction_threshold=thresholds.get("classification", {}).get("context_correction_threshold", 0.7),
            hard_override_confidence=thresholds.get("classification", {}).get("hard_override_confidence", 0.92),
            semantic_signals=config.get("pipeline", {}).get("classification", {}).get("semantic_signals", {}),
            block_majority_boost=thresholds.get("classification", {}).get("block_majority_boost", 0.08),
            table_density_threshold=thresholds.get("classification", {}).get("table_density_threshold", 0.18),
        )
        self.fallback_logic = FallbackLogic()
        self.extractor = ExtractionFusion(
            config=config.get("pipeline", {}).get("extraction", {}),
            thresholds=thresholds.get("extraction", {}),
        )
        self.yolo = YOLODetector()
        self.vision_postprocess = VisionPostProcessor()
        self.vision_validator = VisionValidator(
            thresholds.get("vision", {}).get("min_detection_confidence", 0.55)
        )
        self.date_extractor = DateExtractor()
        self.timeline_builder = SequenceBuilder()
        self.rule_engine = RuleEngine(rules, thresholds)
        self.decision_engine = DecisionEngine(thresholds)
        self.provenance_builder = ProvenanceBuilder()
        self.trace_builder = TraceBuilder()
        self.report_generator = ExplainabilityReportGenerator()
        self.low_confidence_handler = LowConfidenceHandler()
        self.optimizer = PipelineOptimizer(thresholds)
