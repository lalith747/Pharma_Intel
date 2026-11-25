"""Create a blind, PMID-disjoint relation annotation sample from model output."""

from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pharmaintel.relation_extraction import extract_sentence_relations

DEV = ROOT / "data/annotated/relation_annotation_sample.csv"
SENTENCES = ROOT / "data/processed/pubmed/pubmed_sentences.csv"
PREDICTIONS = ROOT / "data/processed/pubmed/bc5cdr_ner_predictions.jsonl"
OUTPUT = ROOT / "data/annotated/relation_holdout_sample.csv"
MANIFEST = ROOT / "data/annotated/relation_holdout_manifest.json"
RANDOM_SEED = 42017
TARGET_ADRS = {
    "neutropenia",
    "neutropenic",
    "agranulocytosis",
    "granulocytopenia",
    "leukopenia",
    "leucopenia",
}
OUTPUT_COLUMNS = [
    "relation_id",
    "sampling_stratum",
    "pmid",
    "title",
    "sentence_index",
    "drug",
    "adr",
    "sentence",
    "gold_status",
    "review_status",
    "annotation_notes",
]


def make_candidates(
    sentence_rows: list[dict[str, Any]], prediction_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Join entities by row order, form model candidate pairs, keep one per PMID."""
    if len(sentence_rows) != len(prediction_rows):
        raise ValueError("Sentence and prediction rows have different lengths.")
    by_pmid: dict[str, list[dict[str, Any]]] = {}
    for source, prediction in zip(sentence_rows, prediction_rows, strict=True):
        text = str(source["sentence"])
        if text != str(prediction.get("sentence", "")) or str(source["pmid"]) != str(
            prediction.get("pmid", "")
        ):
            raise ValueError("Sentence/prediction alignment check failed.")
        for relation in extract_sentence_relations(
            text, prediction.get("entities", []), use_case_study_lexicon=False
        ):
            candidate = {
                "pmid": str(source["pmid"]),
                "title": str(source.get("title", "")),
                "sentence_index": str(source.get("sentence_index", "")),
                "drug": str(relation["drug"]["text"]),
                "adr": str(relation["adr"]["text"]),
                "sentence": text,
            }
            by_pmid.setdefault(candidate["pmid"], []).append(candidate)
    # Deterministic candidate choice per PMID; never include model outputs/cues.
    return [
        min(rows, key=lambda r: (r["sentence_index"], r["drug"].casefold(), r["adr"].casefold()))
        for _, rows in sorted(by_pmid.items())
    ]


def sample_candidates(
    candidates: list[dict[str, Any]],
    excluded_pmids: set[str],
    *,
    target_n: int = 30,
    random_n: int = 30,
    seed: int = RANDOM_SEED,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    eligible = [row for row in candidates if row["pmid"] not in excluded_pmids]
    target = [
        row
        for row in eligible
        if row["drug"].casefold().strip() in {"clozapine", "clozaril", "leponex"}
        and row["adr"].casefold().strip() in TARGET_ADRS
    ]
    target_ids = {row["pmid"] for row in target}
    rng = random.Random(seed)
    target_pick = rng.sample(target, min(target_n, len(target)))
    random_pool = [row for row in eligible if row["pmid"] not in target_ids]
    random_pick = rng.sample(random_pool, min(random_n, len(random_pool)))
    result = [dict(row, sampling_stratum="target_enriched") for row in target_pick]
    result.extend(dict(row, sampling_stratum="random_article") for row in random_pick)
    rng.shuffle(result)
    return result, {
        "eligible_unique_pmids": len(eligible),
        "target_candidate_pmids": len(target),
        "target_selected": len(target_pick),
        "random_pool_pmids": len(random_pool),
        "random_selected": len(random_pick),
    }


def main() -> None:
    for path in (DEV, SENTENCES, PREDICTIONS):
        if not path.exists():
            raise FileNotFoundError(path)
    with DEV.open(encoding="utf-8-sig", newline="") as handle:
        dev_rows = list(csv.DictReader(handle))
    excluded = {str(row["pmid"]) for row in dev_rows}
    frame = pd.read_csv(SENTENCES, dtype={"pmid": str}, keep_default_na=False)
    prediction_rows = [
        json.loads(line)
        for line in PREDICTIONS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    candidates = make_candidates(frame.to_dict(orient="records"), prediction_rows)
    selected, counts = sample_candidates(candidates, excluded)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for index, row in enumerate(selected, start=1):
            writer.writerow(
                {
                    "relation_id": f"HOLDOUT{index:03d}",
                    **{
                        key: row[key]
                        for key in OUTPUT_COLUMNS
                        if key in row
                        and key
                        not in {"relation_id", "gold_status", "review_status", "annotation_notes"}
                    },
                    "gold_status": "",
                    "review_status": "pending",
                    "annotation_notes": "",
                }
            )
    written = pd.read_csv(OUTPUT, dtype={"pmid": str}, keep_default_na=False)
    if written["pmid"].duplicated().any() or set(written["pmid"]) & excluded:
        raise RuntimeError("Holdout PMID uniqueness/disjointness check failed.")
    if written["gold_status"].ne("").any() or not set(written["review_status"]) <= {"pending"}:
        raise RuntimeError("Holdout labels must be blank and all rows pending.")
    if set(written.columns) != set(OUTPUT_COLUMNS):
        raise RuntimeError("Holdout contains unexpected fields that could leak predictions.")
    manifest = {
        "sampling_seed": RANDOM_SEED,
        "stratum_sizes_requested": {"target_enriched": 30, "random_article": 30},
        "stratum_sizes_actual": written["sampling_stratum"].value_counts().to_dict(),
        "counts": counts,
        "development_unique_pmids_excluded": len(excluded),
        "candidate_source": "pinned BC5CDR predictions over PubMed sentences",
        "blinding": "Prediction labels, scores, relation cues and model outputs are not included in the annotation CSV or app.",
        "validation": "One candidate pair per PMID; disjoint from development PMIDs; labels blank; review status pending.",
        "independent_gold_status": "not yet annotated by an independent human reviewer",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"Blind annotation CSV: {OUTPUT}")


if __name__ == "__main__":
    main()
