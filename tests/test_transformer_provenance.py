from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_transformer_corpus_ner import _source_entity


def test_relation_mentions_retain_original_transformer_label_and_score():
    original = {
        "text": "clozapine",
        "label": "DRUG",
        "source_label": "Chemical",
        "start": 5,
        "end": 14,
        "score": 0.97,
    }
    mention = {"text": "clozapine", "start": 5, "end": 14}

    assert _source_entity([original], mention) == original


def test_entity_metadata_lookup_requires_matching_span_offsets():
    entity = {
        "text": "clozapine",
        "label": "DRUG",
        "source_label": "Chemical",
        "start": 5,
        "end": 14,
        "score": 0.97,
    }

    assert _source_entity([entity], {"start": 0, "end": 9}) == {}
