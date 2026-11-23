"""Reproduce the clozapine-neutropenia index and audit its assumptions."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pharmaintel.prioritization import audit_cross_source_index


def main() -> None:
    ranked_path = ROOT / "dashboard/data/transformer_case_study_signals.csv"
    with ranked_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    signal = next(
        row
        for row in rows
        if row["drug"].casefold() == "clozapine" and row["adr"].casefold() == "neutropenia"
    )
    audit = audit_cross_source_index(signal, faers_reports=929, ebgm=50.81)
    out_path = ROOT / "results/evaluation/cross_source_index_audit.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))
    print(f"Saved audit: {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
