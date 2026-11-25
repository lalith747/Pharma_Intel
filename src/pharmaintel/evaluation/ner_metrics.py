"""Strict exact-span evaluation utilities for the PharmaIntel NER annotation schema."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

ENTITY_LABELS = {"DRUG", "ADR"}


def load_and_validate_gold(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse completed human annotations and validate character offsets and labels."""
    gold_rows = []
    for row in rows:
        status = str(row.get("review_status", "")).strip()
        if status != "complete":
            raise ValueError(
                f"{row.get('sample_id', '<unknown>')}: review_status must be complete."
            )
        try:
            entities = json.loads(row.get("gold_entities_json", ""))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{row.get('sample_id', '<unknown>')}: invalid gold_entities_json."
            ) from exc
        if not isinstance(entities, list):
            raise TypeError(
                f"{row.get('sample_id', '<unknown>')}: gold annotation must be a JSON list."
            )
        validated = []
        for entity in entities:
            if not isinstance(entity, dict):
                raise TypeError(
                    f"{row.get('sample_id', '<unknown>')}: each entity must be an object."
                )
            label = entity.get("label")
            start, end = entity.get("start"), entity.get("end")
            text = entity.get("text")
            if label not in ENTITY_LABELS:
                raise ValueError(
                    f"{row.get('sample_id', '<unknown>')}: unsupported label {label!r}."
                )
            if (
                not isinstance(start, int)
                or not isinstance(end, int)
                or not (0 <= start < end <= len(row["sentence"]))
            ):
                raise ValueError(f"{row.get('sample_id', '<unknown>')}: invalid entity offsets.")
            if row["sentence"][start:end] != text:
                raise ValueError(
                    f"{row.get('sample_id', '<unknown>')}: span text does not match offsets."
                )
            validated.append((start, end, label))
        gold_rows.append({**row, "gold_spans": set(validated)})
    if not gold_rows:
        raise ValueError("No annotated rows were provided.")
    return gold_rows


def exact_span_metrics(
    gold: Iterable[tuple[int, int, str]], predicted: Iterable[tuple[int, int, str]]
) -> dict[str, Any]:
    """Calculate exact-boundary precision, recall, and F1 for one label set."""
    gold_set, predicted_set = set(gold), set(predicted)
    tp = len(gold_set & predicted_set)
    fp = len(predicted_set - gold_set)
    fn = len(gold_set - predicted_set)
    support = len(gold_set)
    precision = tp / (tp + fp) if tp + fp else (0.0 if support else None)
    recall = tp / support if support else None
    f1 = (
        (2 * precision * recall / (precision + recall))
        if precision is not None and recall is not None and precision + recall
        else (0.0 if support and precision is not None else None)
    )
    return {
        "support": support,
        "predicted": len(predicted_set),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def evaluate_prediction_rows(
    gold_rows: list[dict[str, Any]], prediction_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Score each model separately by random/enriched stratum and entity label."""
    gold_by_id = {str(row["sample_id"]): row for row in gold_rows}
    predictions_by_model: dict[str, dict[str, list[tuple[int, int, str]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for prediction in prediction_rows:
        sample_id = str(prediction["sample_id"])
        if sample_id not in gold_by_id:
            raise ValueError(f"Prediction has unknown sample_id {sample_id}.")
        model_id = str(prediction["model_id"])
        for entity in prediction.get("entities", []):
            label = entity.get("label")
            if label not in ENTITY_LABELS:
                continue
            predictions_by_model[model_id][sample_id].append(
                (int(entity["start"]), int(entity["end"]), str(label))
            )

    metrics = []
    for model_id, model_predictions in sorted(predictions_by_model.items()):
        for stratum in sorted({str(row["sampling_stratum"]) for row in gold_rows}):
            rows = [row for row in gold_rows if str(row["sampling_stratum"]) == stratum]
            for label in sorted(ENTITY_LABELS):
                gold = [
                    (start, end, entity_label)
                    for row in rows
                    for start, end, entity_label in row["gold_spans"]
                    if entity_label == label
                ]
                predicted = [
                    span
                    for row in rows
                    for span in model_predictions.get(str(row["sample_id"]), [])
                    if span[2] == label
                ]
                metrics.append(
                    {
                        "model_id": model_id,
                        "sampling_stratum": stratum,
                        "label": label,
                        "sample_rows": len(rows),
                        **exact_span_metrics(gold, predicted),
                    }
                )
    return metrics
