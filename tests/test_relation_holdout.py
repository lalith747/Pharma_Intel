from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_relation_holdout import OUTPUT_COLUMNS, sample_candidates


def test_holdout_sampling_is_repeatable_unique_and_excludes_development_pmids():
    rows = [
        {
            "pmid": str(i),
            "drug": "clozapine" if i <= 10 else "aspirin",
            "adr": "neutropenia" if i <= 10 else "headache",
            "sentence": f"s{i}",
        }
        for i in range(1, 21)
    ]
    first, counts = sample_candidates(rows, {"1", "2"}, target_n=5, random_n=5, seed=11)
    second, _ = sample_candidates(rows, {"1", "2"}, target_n=5, random_n=5, seed=11)
    assert first == second
    assert len(first) == len({row["pmid"] for row in first}) == 10
    assert not ({row["pmid"] for row in first} & {"1", "2"})
    assert counts["target_selected"] == 5
    assert counts["random_selected"] == 5


def test_blind_review_schema_has_no_prediction_fields():
    assert OUTPUT_COLUMNS == [
        "relation_id", "sampling_stratum", "pmid", "title", "sentence_index",
        "drug", "adr", "sentence", "gold_status", "review_status", "annotation_notes",
    ]
    assert not any("predict" in column or "score" in column for column in OUTPUT_COLUMNS)
