"""Document classification ensemble."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any

from src.classification.cnn_fallback import CNNFallbackClassifier
from src.classification.keyword_rules import KeywordRuleClassifier
from src.classification.layoutlmv3 import LayoutLMv3Classifier
from src.core.state_manager import ClassificationResult, FieldCandidate, OCRPageResult


class ClassificationEnsemble:
    """Combine semantic, visual, and rule-based classifiers."""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        keyword_override_gap: float = 0.12,
        class_weights: dict[str, dict[str, float]] | None = None,
        keyword_boosts: dict[str, list[str]] | None = None,
        rerank_margin: float = 0.18,
        hard_overrides: dict[str, list[str]] | None = None,
        class_thresholds: dict[str, float] | None = None,
        context_correction_threshold: float = 0.7,
        hard_override_confidence: float = 0.92,
        semantic_signals: dict[str, dict[str, list[str]]] | None = None,
        block_majority_boost: float = 0.08,
        table_density_threshold: float = 0.18,
    ) -> None:
        self.models = [
            LayoutLMv3Classifier(),
            CNNFallbackClassifier(),
            KeywordRuleClassifier(keyword_boosts, hard_overrides),
        ]
        self.weights = weights or {"layoutlmv3": 1.0, "cnn": 0.65, "keyword_rules": 0.8}
        self.keyword_override_gap = keyword_override_gap
        self.class_weights = class_weights or {}
        self.rerank_margin = rerank_margin
        self.hard_overrides = hard_overrides or {}
        self.class_thresholds = class_thresholds or {}
        self.context_correction_threshold = context_correction_threshold
        self.hard_override_confidence = hard_override_confidence
        self.semantic_signals = semantic_signals or {}
        self.block_majority_boost = block_majority_boost
        self.table_density_threshold = table_density_threshold

    def predict(self, ocr_result: OCRPageResult) -> ClassificationResult:
        """Vote across classifiers and return an aggregated result."""
        candidates = [model.predict(ocr_result) for model in self.models]
        page_result = self._aggregate(candidates, ocr_result.page_number)
        return self._apply_block_reasoning(page_result, ocr_result)

    def predict_batch(self, ocr_results: list[OCRPageResult]) -> list[ClassificationResult]:
        """Predict labels for a batch of OCR results."""
        return [self.predict(item) for item in ocr_results]

    def apply_history_adjustments(self, history_analysis: dict[str, Any]) -> dict[str, float]:
        """Adjust ensemble weights using recent optimizer history."""
        changes: dict[str, float] = {}
        common_issues = dict(history_analysis.get("common_issues", []))
        if common_issues.get("conflicting_classification_votes", 0) >= 5:
            self.weights["cnn"] = round(max(0.3, self.weights.get("cnn", 0.65) - 0.05), 4)
            self.weights["keyword_rules"] = round(min(1.0, self.weights.get("keyword_rules", 0.8) + 0.03), 4)
            changes["cnn"] = self.weights["cnn"]
            changes["keyword_rules"] = self.weights["keyword_rules"]
        if common_issues.get("low_confidence_prediction", 0) >= 5:
            self.weights["layoutlmv3"] = round(min(1.08, self.weights.get("layoutlmv3", 1.0) + 0.02), 4)
            changes["layoutlmv3"] = self.weights["layoutlmv3"]
        return changes

    def _aggregate(self, candidates: list[ClassificationResult], page_number: int) -> ClassificationResult:
        """Aggregate candidate predictions with adaptive weighting."""
        label_scores: dict[str, float] = defaultdict(float)
        raw_label_scores: dict[str, float] = defaultdict(float)
        per_model: list[dict[str, object]] = []
        evidence: list[str] = []
        hard_override_label = self._hard_override_label(candidates)
        if hard_override_label:
            return ClassificationResult(
                page_number=page_number,
                label=hard_override_label,
                confidence=self.hard_override_confidence,
                evidence=[f"hard_override:{hard_override_label}", "adaptive_weighting:forced"],
                metadata={
                    "votes": [
                        {
                            "model": str(candidate.metadata.get("model", "unknown")),
                            "label": candidate.label,
                            "confidence": candidate.confidence,
                            "hard_override": bool(candidate.metadata.get("hard_override")),
                        }
                        for candidate in candidates
                    ],
                    "aggregated_scores": {hard_override_label: self.hard_override_confidence},
                    "raw_label_scores": {hard_override_label: self.hard_override_confidence},
                    "agreement_ratio": 1.0,
                    "hard_override": True,
                },
            )
        for candidate in candidates:
            model_name = str(candidate.metadata.get("model", "unknown"))
            per_class_weight = self.class_weights.get(candidate.label, {}).get(model_name, 1.0)
            weighted_confidence = candidate.confidence * self.weights.get(model_name, 0.5) * per_class_weight
            label_scores[candidate.label] += weighted_confidence
            raw_label_scores[candidate.label] += candidate.confidence
            per_model.append(
                {
                    "model": model_name,
                    "label": candidate.label,
                    "confidence": candidate.confidence,
                    "per_class_weight": per_class_weight,
                    "weighted_confidence": round(weighted_confidence, 4),
                }
            )
            evidence.extend(candidate.evidence)
        ranked = sorted(label_scores.items(), key=lambda item: item[1], reverse=True)
        label, score = ranked[0]
        agreement_ratio = self._agreement_ratio(candidates)
        reranked_label = self._rerank_by_consensus(raw_label_scores, label_scores, agreement_ratio)
        if reranked_label != label:
            label = reranked_label
            score = label_scores[reranked_label]
            evidence.append("confidence_rerank:activated")
        keyword_candidate = next(
            (candidate for candidate in candidates if candidate.metadata.get("model") == "keyword_rules"),
            None,
        )
        if keyword_candidate and keyword_candidate.label != label:
            winner_score = ranked[0][1]
            keyword_score = label_scores.get(keyword_candidate.label, 0.0)
            if winner_score - keyword_score <= self.keyword_override_gap:
                label = keyword_candidate.label
                score = keyword_score
                evidence.append("keyword_override:activated")
        heuristics = self._structure_heuristics(candidates)
        for heuristic_label, boost in heuristics["boosts"].items():
            label_scores[heuristic_label] += boost
        if heuristics["boosts"]:
            reranked = sorted(label_scores.items(), key=lambda item: item[1], reverse=True)
            label, score = reranked[0]
            evidence.extend(heuristics["evidence"])
        semantic_adjustments = self._semantic_adjustments(candidates)
        for semantic_label, adjustment in semantic_adjustments["adjustments"].items():
            label_scores[semantic_label] += adjustment
        if semantic_adjustments["adjustments"]:
            reranked = sorted(label_scores.items(), key=lambda item: item[1], reverse=True)
            label, score = reranked[0]
            evidence.extend(semantic_adjustments["evidence"])
        if agreement_ratio >= 0.67:
            score += (self.keyword_override_gap + 0.04) * agreement_ratio
            evidence.append("adaptive_weighting:agreement_boost")
        else:
            score -= self.keyword_override_gap * (0.5 + (1 - agreement_ratio))
            evidence.append("adaptive_weighting:disagreement_penalty")
        confidence = self._final_confidence(score, agreement_ratio, label_scores, label)
        return ClassificationResult(
            page_number=page_number,
            label=label,
            confidence=confidence,
            evidence=evidence,
            metadata={
                "votes": per_model,
                "aggregated_scores": dict(sorted(label_scores.items(), key=lambda item: item[1], reverse=True)),
                "raw_label_scores": dict(raw_label_scores),
                "agreement_ratio": round(agreement_ratio, 4),
                "class_threshold": self.class_thresholds.get(label, 0.6),
                "vote_breakdown": per_model,
                "structure_heuristics": heuristics,
                "semantic_adjustments": semantic_adjustments,
            },
        )

    def _apply_block_reasoning(self, page_result: ClassificationResult, ocr_result: OCRPageResult) -> ClassificationResult:
        """Use block-level and segment-level voting to refine page classification."""
        blocks = self._segment_blocks(ocr_result)
        if not blocks:
            return page_result
        block_results: list[ClassificationResult] = []
        for block_name, block_text in blocks.items():
            block_candidates = [model.predict(self._as_block_ocr(ocr_result, block_text)) for model in self.models]
            block_result = self._aggregate(block_candidates, ocr_result.page_number)
            block_result.metadata["block_name"] = block_name
            block_results.append(block_result)
        majority_label, majority_ratio = self._majority_label(block_results)
        table_density = self._table_density(ocr_result.full_text)
        segment_signals = self._segment_split_signals(ocr_result)
        refined = deepcopy(page_result)
        refined.metadata["block_results"] = [
            {
                "block": item.metadata.get("block_name"),
                "label": item.label,
                "confidence": item.confidence,
            }
            for item in block_results
        ]
        refined.metadata["table_density"] = round(table_density, 4)
        refined.metadata["segment_signals"] = segment_signals
        if majority_ratio >= 0.5 and majority_label != refined.label:
            refined.label = majority_label
            refined.evidence.append(f"block_majority:{majority_label}")
            refined.confidence = min(0.99, max(refined.confidence, refined.confidence + self.block_majority_boost))
        elif majority_ratio >= 0.5:
            refined.confidence = min(0.99, refined.confidence + self.block_majority_boost * majority_ratio)
            refined.evidence.append("block_majority:agreement_boost")
        if table_density >= self.table_density_threshold and refined.label == "bill":
            refined.confidence = min(0.99, refined.confidence + 0.05)
            refined.evidence.append("table_density:bill_boost")
        if table_density < self.table_density_threshold and refined.label in {"procedure_note", "discharge_summary"}:
            refined.confidence = min(0.99, refined.confidence + 0.03)
            refined.evidence.append("text_density:clinical_note_boost")
        strong_segments = [label for label, score in segment_signals.items() if score >= 2]
        if len(strong_segments) > 1:
            refined.metadata["mixed_document_detected"] = True
            refined.evidence.append("segment_split:mixed_document_detected")
            refined.confidence = max(self.class_thresholds.get(refined.label, 0.6), refined.confidence - 0.06)
        return refined

    def correct_with_context(
        self,
        classification: ClassificationResult,
        ocr_result: OCRPageResult,
        extracted_fields: list[FieldCandidate],
    ) -> ClassificationResult:
        """Use extracted fields and rule-like cues to correct low-confidence classifications."""
        if classification.confidence >= self.context_correction_threshold:
            return classification
        inferred_label, inferred_reason = self._infer_from_context(ocr_result, extracted_fields)
        if not inferred_label:
            return classification
        updated = ClassificationResult(
            page_number=classification.page_number,
            label=inferred_label,
            confidence=max(classification.confidence, self.class_thresholds.get(inferred_label, 0.6), 0.74),
            evidence=[*classification.evidence, f"context_correction:{inferred_reason}"],
            metadata={**classification.metadata, "context_correction": {"label": inferred_label, "reason": inferred_reason}},
        )
        return updated

    @staticmethod
    def _agreement_ratio(candidates: list[ClassificationResult]) -> float:
        """Return fraction of votes backing the majority label."""
        counts: dict[str, int] = defaultdict(int)
        for candidate in candidates:
            counts[candidate.label] += 1
        return max(counts.values()) / len(candidates) if candidates else 0.0

    def _rerank_by_consensus(
        self,
        raw_label_scores: dict[str, float],
        weighted_label_scores: dict[str, float],
        agreement_ratio: float,
    ) -> str:
        """Rerank labels using consensus-sensitive margins."""
        ranked = sorted(weighted_label_scores.items(), key=lambda item: item[1], reverse=True)
        if len(ranked) == 1:
            return ranked[0][0]
        winner, winner_score = ranked[0]
        runner_up, runner_score = ranked[1]
        margin = winner_score - runner_score
        if margin <= self.rerank_margin:
            if raw_label_scores.get(runner_up, 0.0) > raw_label_scores.get(winner, 0.0) and agreement_ratio < 1.0:
                return runner_up
        return winner

    @staticmethod
    def _hard_override_label(candidates: list[ClassificationResult]) -> str | None:
        """Return override label when a hard keyword trigger exists."""
        for candidate in candidates:
            if candidate.metadata.get("hard_override"):
                return candidate.label
        return None

    @staticmethod
    def _structure_heuristics(candidates: list[ClassificationResult]) -> dict[str, Any]:
        """Boost labels based on structure-aware signals embedded in evidence."""
        boosts: dict[str, float] = defaultdict(float)
        evidence: list[str] = []
        text = " ".join(
            item
            for candidate in candidates
            for item in candidate.evidence
            if not item.startswith(("layoutlmv3:", "cnn:", "keywords:"))
        ).lower()
        if "amount" in text or "invoice" in text or "final bill" in text:
            boosts["bill"] += 0.18
            evidence.append("structure_heuristic:bill_amount_table")
        if "discharge summary" in text or "discharge date" in text:
            boosts["discharge_summary"] += 0.16
            evidence.append("structure_heuristic:discharge_header")
        if "procedure note" in text or "surgeon" in text or "operation note" in text:
            boosts["procedure_note"] += 0.16
            evidence.append("structure_heuristic:procedure_layout")
        if "claim form" in text or ("patient name" in text and "admission date" in text):
            boosts["claim_form"] += 0.15
            evidence.append("structure_heuristic:claim_form_layout")
        return {"boosts": dict(boosts), "evidence": evidence}

    def _semantic_adjustments(self, candidates: list[ClassificationResult]) -> dict[str, Any]:
        """Adjust scores using contextual positive and negative signals."""
        adjustments: dict[str, float] = defaultdict(float)
        evidence: list[str] = []
        text = " ".join(
            item
            for candidate in candidates
            for item in candidate.evidence
            if not item.startswith(("layoutlmv3:", "cnn:", "keywords:", "hard_override:"))
        ).lower()
        for label, signal_map in self.semantic_signals.items():
            positive_hits = sum(1 for token in signal_map.get("positive", []) if token in text)
            negative_hits = sum(1 for token in signal_map.get("negative", []) if token in text)
            adjustment = positive_hits * 0.06 - negative_hits * 0.05
            if adjustment:
                adjustments[label] += adjustment
                evidence.append(
                    f"semantic_signal:{label}:pos={positive_hits}:neg={negative_hits}:adj={round(adjustment, 3)}"
                )
        return {"adjustments": dict(adjustments), "evidence": evidence}

    @staticmethod
    def _segment_blocks(ocr_result: OCRPageResult) -> dict[str, str]:
        """Split OCR text into header/body/table/footer style blocks."""
        tokens = ocr_result.full_text.split()
        if len(tokens) < 8:
            return {"body": ocr_result.full_text}
        header = " ".join(tokens[: min(8, len(tokens))])
        footer = " ".join(tokens[-min(6, len(tokens)) :])
        middle_tokens = tokens[min(8, len(tokens)) : -min(6, len(tokens))] if len(tokens) > 14 else tokens[min(4, len(tokens)) :]
        middle_text = " ".join(middle_tokens)
        table_chunks = [chunk.strip() for chunk in ocr_result.full_text.split("|") if chunk.strip()]
        blocks = {"header": header, "body": middle_text or ocr_result.full_text, "footer": footer}
        if len(table_chunks) >= 3:
            blocks["table"] = " | ".join(table_chunks)
        return blocks

    @staticmethod
    def _as_block_ocr(ocr_result: OCRPageResult, text: str) -> OCRPageResult:
        """Create a block-scoped OCR view."""
        return OCRPageResult(
            page_number=ocr_result.page_number,
            full_text=text,
            words=ocr_result.words,
            confidence=ocr_result.confidence,
            source=ocr_result.source,
            image_path=ocr_result.image_path,
            metadata=ocr_result.metadata,
        )

    @staticmethod
    def _majority_label(block_results: list[ClassificationResult]) -> tuple[str, float]:
        """Return majority block label and its support ratio."""
        counts: dict[str, int] = defaultdict(int)
        for item in block_results:
            counts[item.label] += 1
        if not counts:
            return "other", 0.0
        label, count = max(counts.items(), key=lambda item: item[1])
        return label, count / len(block_results)

    @staticmethod
    def _table_density(text: str) -> float:
        """Estimate how table-heavy a page is."""
        separators = text.count("|") + text.count(":")
        numeric_tokens = sum(1 for token in text.split() if any(char.isdigit() for char in token))
        total_tokens = max(len(text.split()), 1)
        return (separators + numeric_tokens) / total_tokens

    @staticmethod
    def _segment_split_signals(ocr_result: OCRPageResult) -> dict[str, int]:
        """Detect multiple strong label cues inside one page."""
        text = ocr_result.full_text.lower()
        signals = {
            "claim_form": sum(1 for token in ("claim form", "admission", "beneficiary", "claim id") if token in text),
            "discharge_summary": sum(1 for token in ("discharge", "summary", "final diagnosis") if token in text),
            "procedure_note": sum(1 for token in ("procedure", "operation", "surgeon") if token in text),
            "bill": sum(1 for token in ("amount", "invoice", "total", "bill") if token in text),
        }
        return signals

    def _final_confidence(
        self,
        score: float,
        agreement_ratio: float,
        label_scores: dict[str, float],
        label: str,
    ) -> float:
        """Compute calibrated label confidence with class thresholds."""
        ranked = sorted(label_scores.items(), key=lambda item: item[1], reverse=True)
        margin = ranked[0][1] - ranked[1][1] if len(ranked) > 1 else ranked[0][1]
        base = score / max(len(self.models), 1)
        base += min(0.12, margin * 0.08)
        if agreement_ratio >= 0.67:
            base += 0.05
        threshold = self.class_thresholds.get(label, 0.6)
        return min(max(base, threshold), 0.99)

    @staticmethod
    def _infer_from_context(
        ocr_result: OCRPageResult,
        extracted_fields: list[FieldCandidate],
    ) -> tuple[str | None, str | None]:
        """Infer a document class from extracted fields and rule-like cues."""
        text = ocr_result.full_text.lower()
        fields_by_name: dict[str, list[FieldCandidate]] = defaultdict(list)
        for item in extracted_fields:
            fields_by_name[item.field_name].append(item)
        if fields_by_name.get("amounts") and (
            "bill" in text or "amount" in text or "invoice" in text or "total" in text
        ):
            return "bill", "amount_and_billing_cues"
        if fields_by_name.get("procedure") and fields_by_name.get("amounts"):
            return "bill", "procedure_with_amounts_billing_layout"
        if fields_by_name.get("procedure") and ("surgeon" in text or "procedure note" in text or "operation" in text):
            return "procedure_note", "procedure_field_and_surgical_cues"
        if fields_by_name.get("diagnosis") and "discharge" in text:
            return "discharge_summary", "diagnosis_with_discharge_cues"
        if fields_by_name.get("patient_name") and "admission date" in text:
            return "claim_form", "patient_and_admission_cues"
        return None, None
