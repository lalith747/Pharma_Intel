"""Descriptive metrics for the rule-based relation pilot."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any

RELATION_STATUSES = ("supported", "negated", "speculative", "co_mention")
RELATION_PRESENT = {"supported", "negated", "speculative"}


def _binary_metrics(gold: Iterable[bool], predicted: Iterable[bool]) -> dict[str, Any]:
    pairs = list(zip(gold, predicted, strict=True))
    tp = sum(expected and actual for expected, actual in pairs)
    fp = sum(not expected and actual for expected, actual in pairs)
    fn = sum(expected and not actual for expected, actual in pairs)
    tn = sum(not expected and not actual for expected, actual in pairs)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None
    return {
        "support": len(pairs), "true_positive": tp, "false_positive": fp,
        "false_negative": fn, "true_negative": tn,
        "precision": precision, "recall": recall, "f1": f1,
    }


def _status_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    confusion = {gold: {predicted: 0 for predicted in RELATION_STATUSES} for gold in RELATION_STATUSES}
    for row in rows:
        gold, predicted = row["gold_status"], row["predicted_status"]
        if gold in confusion and predicted in confusion[gold]:
            confusion[gold][predicted] += 1
    total = len(rows)
    correct = sum(confusion[label][label] for label in RELATION_STATUSES)
    class_metrics = {}
    f1_values = []
    for label in RELATION_STATUSES:
        tp = confusion[label][label]
        support = sum(confusion[label].values())
        predicted_count = sum(confusion[gold][label] for gold in RELATION_STATUSES)
        precision = tp / predicted_count if predicted_count else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        class_metrics[label] = {
            "support": support,
            "predicted": predicted_count,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
        if support:
            f1_values.append(f1)
    return {
        "support": total,
        "accuracy": correct / total if total else None,
        "macro_f1_over_present_classes": sum(f1_values) / len(f1_values) if f1_values else None,
        "classes": class_metrics,
        "confusion_matrix": confusion,
    }


def evaluate_relation_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Score relation mention detection, four-way status, context, and errors.

    Unclear examples are excluded from metrics. Binary relation mention means
    the sentence explicitly addresses a drug–ADR relation, including negated or
    speculative statements. These descriptive figures are not population
    estimates and do not measure causality.
    """
    invalid = [
        row for row in rows
        if row.get("gold_status") not in {*RELATION_STATUSES, "unclear"}
        or row.get("predicted_status") not in RELATION_STATUSES
    ]
    if invalid:
        raise ValueError(f"Invalid relation annotation or prediction: {invalid[0]}")

    by_stratum: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_stratum.setdefault(str(row["sampling_stratum"]), []).append(row)
    clear_rows = [row for row in rows if row["gold_status"] != "unclear"]
    relation_rows = [row for row in clear_rows if row["gold_status"] in RELATION_PRESENT]

    def metrics_for(group: list[dict[str, Any]]) -> dict[str, Any]:
        labeled = [row for row in group if row["gold_status"] != "unclear"]
        relation_positive = [row for row in labeled if row["gold_status"] in RELATION_PRESENT]
        binary = _binary_metrics(
            (row["gold_status"] in RELATION_PRESENT for row in labeled),
            (row["predicted_status"] != "co_mention" for row in labeled),
        )
        context_correct = sum(row["gold_status"] == row["predicted_status"] for row in relation_positive)
        return {
            "candidate_pairs": len(group),
            "unclear_excluded": len(group) - len(labeled),
            "relation_mention_detection": binary,
            "four_way_status": _status_metrics(labeled),
            "joint_status_accuracy_on_gold_relation_pairs": {
                "support": len(relation_positive),
                "correct": context_correct,
                "accuracy": context_correct / len(relation_positive) if relation_positive else None,
            },
        }

    error_rows = []
    for row in clear_rows:
        if row["gold_status"] != row["predicted_status"]:
            error_rows.append(
                {
                    "relation_id": row["relation_id"], "sample_id": row["sample_id"],
                    "sampling_stratum": row["sampling_stratum"], "pmid": row["pmid"],
                    "drug": row["drug"], "adr": row["adr"],
                    "gold_status": row["gold_status"], "predicted_status": row["predicted_status"],
                    "predicted_relation_cues": row["predicted_relation_cues"],
                    "predicted_context_cues": row["predicted_context_cues"],
                    "sentence": row["sentence"],
                }
            )

    return {
        "evaluation_scope": "assistant-curated pilot; same sentences as the NER sample; not independent human gold",
        "candidate_pairs": len(rows),
        "unique_pmids": len({row["pmid"] for row in rows}),
        "unclear_excluded_overall": len(rows) - len(clear_rows),
        "descriptive_all_strata_combined": metrics_for(rows),
        "by_stratum": {name: metrics_for(group) for name, group in sorted(by_stratum.items())},
        "error_count_among_non_unclear": len(error_rows),
        "errors": error_rows,
    }
