"""Evaluate the sentence-level relation baseline on the provisional pilot."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pharmaintel.evaluation.relation_metrics import evaluate_relation_rows

INPUT = PROJECT_ROOT / "data/annotated/relation_annotation_sample.csv"
METRICS_OUTPUT = PROJECT_ROOT / "results/evaluation/relation_metrics.json"
ERRORS_OUTPUT = PROJECT_ROOT / "results/evaluation/relation_error_analysis.csv"


def main() -> None:
    with INPUT.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    report = evaluate_relation_rows(rows)
    errors = report.pop("errors")
    METRICS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    METRICS_OUTPUT.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if errors:
        with ERRORS_OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(errors[0]))
            writer.writeheader()
            writer.writerows(errors)
    else:
        ERRORS_OUTPUT.write_text(
            "relation_id,sample_id,sampling_stratum,pmid,drug,adr,gold_status,predicted_status,predicted_relation_cues,predicted_context_cues,sentence\n",
            encoding="utf-8",
        )
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "candidate_pairs",
                    "unique_pmids",
                    "unclear_excluded_overall",
                    "descriptive_all_strata_combined",
                    "by_stratum",
                    "error_count_among_non_unclear",
                )
            },
            indent=2,
        )
    )
    print(f"Wrote metrics to {METRICS_OUTPUT}")
    print(f"Wrote error analysis to {ERRORS_OUTPUT}")


if __name__ == "__main__":
    main()
