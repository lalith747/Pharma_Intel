"""Run the case-study rule baseline and shortlisted Hugging Face NER models.

This command deliberately requires reviewed gold labels before it downloads models
or writes predictions, preserving a blind annotation workflow.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
from pathlib import Path
from typing import Any

from pharmaintel.evaluation.ner_metrics import evaluate_prediction_rows, load_and_validate_gold
from pharmaintel.ner.huggingface import MODEL_CANDIDATES, predict_entities
from pharmaintel.ner.rule_baseline import extract_case_study_entities


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _run(args: argparse.Namespace) -> None:
    annotation_rows = _read_csv(Path(args.annotations))
    gold_rows = load_and_validate_gold(annotation_rows)
    expected_ids = {row["sample_id"] for row in annotation_rows}
    completed_ids = {row["sample_id"] for row in gold_rows}
    if expected_ids != completed_ids:
        raise ValueError("Every sample row must have a completed gold annotation before benchmarking.")

    all_predictions: list[dict[str, Any]] = []
    provenance: list[dict[str, str]] = [
        {
            "model_id": "pharmaintel/case-study-lexical-baseline",
            "model_revision": "lexicon-v1",
            "notes": "Target aliases only; not a general biomedical NER baseline.",
        }
    ]
    for row in annotation_rows:
        all_predictions.append(
            {
                "sample_id": row["sample_id"],
                "model_id": "pharmaintel/case-study-lexical-baseline",
                "entities": extract_case_study_entities(row["sentence"]),
            }
        )

    texts = [row["sentence"] for row in annotation_rows]
    for model_id in args.models:
        model_outputs, model_info = predict_entities(
            texts,
            model_id=model_id,
            batch_size=args.batch_size,
            device=-1 if args.device == "cpu" else int(args.device.split(":", 1)[1]),
            revision=args.revision,
        )
        provenance.append(
            {
                "model_id": model_info["model_id"],
                "model_revision": model_info["model_revision"],
                "tokenizer_class": model_info["tokenizer_class"],
                "aggregation_strategy": model_info["aggregation_strategy"],
                "device": model_info["device"],
                "stride": model_info["stride"],
                "notes": "Confidence is a model score, not a probability of a true or causal relation.",
            }
        )
        for row, entities in zip(annotation_rows, model_outputs, strict=True):
            all_predictions.append(
                {"sample_id": row["sample_id"], "model_id": model_id, "entities": entities}
            )

    metrics = evaluate_prediction_rows(gold_rows, all_predictions)
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    with (output_path / "ner_predictions.jsonl").open("w", encoding="utf-8") as handle:
        for prediction in all_predictions:
            handle.write(json.dumps(prediction, ensure_ascii=False) + "\n")
    _write_csv(output_path / "ner_metrics.csv", metrics)
    (output_path / "ner_model_provenance.json").write_text(
        json.dumps(
            {
                "python_version": platform.python_version(),
                "transformers_version": __import__("transformers").__version__,
                "torch_version": __import__("torch").__version__,
                "metrics": "strict exact-span P/R/F1, split by sampling stratum and entity type",
                "confidence_interpretation": "model score only; not causal probability",
                "models": provenance,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Saved {len(all_predictions)} prediction rows and {len(metrics)} metric rows to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", default="data/annotated/ner_annotation_sample.csv")
    parser.add_argument("--output-dir", default="results/evaluation")
    parser.add_argument("--models", nargs="+", default=list(MODEL_CANDIDATES))
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--device", default="cpu", help="cpu or cuda:N (CUDA must be available).")
    parser.add_argument("--revision", default=None, help="Optional Hugging Face commit or tag.")
    args = parser.parse_args()
    try:
        _run(args)
    except (ValueError, TypeError, RuntimeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
