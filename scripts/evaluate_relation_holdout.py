"""Score the blinded holdout only after all annotations have been completed."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pharmaintel.evaluation.relation_metrics import evaluate_relation_rows
from pharmaintel.relation_extraction import extract_sentence_relations

ANNOTATIONS = ROOT / "data/annotated/relation_holdout_sample.csv"
PREDICTIONS = ROOT / "data/processed/pubmed/bc5cdr_ner_predictions.jsonl"
DEVELOPMENT = ROOT / "data/annotated/relation_annotation_sample.csv"
OUTPUT = ROOT / "results/evaluation/relation_holdout_metrics.json"
ERRORS = ROOT / "results/evaluation/relation_holdout_errors.csv"
VALID_LABELS = {"supported", "negated", "speculative", "co_mention", "unclear"}


def _status(relation: dict[str, Any]) -> str:
    if relation["evidence_class"] == "co_mention_only":
        return "co_mention"
    if relation["assertion"] in {"negated", "speculative"}:
        return relation["assertion"]
    return "supported"


def build_evaluation_rows(
    annotations: pd.DataFrame, prediction_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    lookup = {(str(row["pmid"]), str(row["sentence_index"])): row for row in prediction_rows}
    results = []
    for row in annotations.to_dict(orient="records"):
        key = (str(row["pmid"]), str(row["sentence_index"]))
        prediction = lookup.get(key)
        if prediction is None or prediction.get("sentence") != row["sentence"]:
            raise ValueError(f"Pinned NER prediction missing or sentence mismatch for {key}.")
        relations = extract_sentence_relations(
            str(row["sentence"]), prediction.get("entities", []), use_case_study_lexicon=False
        )
        matches = [
            relation
            for relation in relations
            if relation["drug"]["text"].casefold() == str(row["drug"]).casefold()
            and relation["adr"]["text"].casefold() == str(row["adr"]).casefold()
        ]
        if not matches:
            raise ValueError(f"Candidate pair is not reproducible from pinned model output: {key}.")
        results.append(
            {
                "relation_id": row["relation_id"],
                "sample_id": row["relation_id"],
                "sampling_stratum": row["sampling_stratum"],
                "pmid": str(row["pmid"]),
                "drug": row["drug"],
                "adr": row["adr"],
                "sentence": row["sentence"],
                "gold_status": row["gold_status"],
                "predicted_status": _status(matches[0]),
                "predicted_relation_cues": json.dumps(
                    matches[0]["relation_cues"], ensure_ascii=False
                ),
                "predicted_context_cues": json.dumps(
                    matches[0]["context_cues"], ensure_ascii=False
                ),
            }
        )
    return results


def main() -> None:
    for path in (ANNOTATIONS, PREDICTIONS, DEVELOPMENT):
        if not path.exists():
            raise FileNotFoundError(path)
    annotations = pd.read_csv(ANNOTATIONS, dtype={"pmid": str}, keep_default_na=False)
    if annotations.empty or annotations["review_status"].ne("complete").any():
        pending = int(annotations["review_status"].ne("complete").sum())
        raise ValueError(f"Holdout scoring blocked: {pending} row(s) still need review.")
    if not annotations["gold_status"].isin(VALID_LABELS).all():
        raise ValueError("Every completed row must have one valid gold status.")
    if annotations["pmid"].duplicated().any():
        raise ValueError("Holdout must contain at most one candidate pair per PMID.")
    dev = pd.read_csv(DEVELOPMENT, dtype={"pmid": str}, keep_default_na=False)
    overlap = set(annotations["pmid"]) & set(dev["pmid"])
    if overlap:
        raise ValueError(f"Holdout overlaps development PMIDs: {sorted(overlap)[:5]}.")
    prediction_rows = [
        json.loads(line)
        for line in PREDICTIONS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = build_evaluation_rows(annotations, prediction_rows)
    report = evaluate_relation_rows(rows)
    report["evaluation_scope"] = (
        "PMID-disjoint annotation set; relation-rule development sample excluded. Metrics remain descriptive "
        "and depend on the annotator's review. Independent-human status must be stated by the project team."
    )
    report["model_under_evaluation"] = (
        "pinned BC5CDR candidate extraction + pair-scoped lexical relation/assertion baseline"
    )
    report["not_measured"] = [
        "clinical causality",
        "population-level safety risk",
        "generalization beyond sampled PubMed records",
    ]
    errors = report.pop("errors")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with ERRORS.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = list(errors[0]) if errors else ["relation_id", "gold_status", "predicted_status"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(errors)
    print(
        json.dumps(
            {
                "candidate_pairs": report["candidate_pairs"],
                "unique_pmids": report["unique_pmids"],
                "by_stratum": report["by_stratum"],
                "scope": report["evaluation_scope"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
