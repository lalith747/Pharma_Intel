import pytest

from pharmaintel.evaluation.ner_metrics import exact_span_metrics, load_and_validate_gold
from pharmaintel.ner.huggingface import map_candidate_label
from pharmaintel.ner.rule_baseline import extract_case_study_entities


def test_case_study_rule_baseline_returns_exact_offsets_and_preserves_case():
    sentence = "CLOZAPINE was stopped after neutropenia was observed."

    entities = extract_case_study_entities(sentence)

    assert [(entity["text"], entity["label"]) for entity in entities] == [
        ("CLOZAPINE", "DRUG"),
        ("neutropenia", "ADR"),
    ]
    assert all(sentence[entity["start"] : entity["end"]] == entity["text"] for entity in entities)


def test_model_label_mapping_keeps_target_classes_and_rejects_other_labels():
    assert map_candidate_label("Glasgow-AI4BioMed/bioner_bc5cdr", "Chemical") == "DRUG"
    assert map_candidate_label("Glasgow-AI4BioMed/bioner_bc5cdr", "Disease") == "ADR"
    assert map_candidate_label("d4data/biomedical-ner-all", "Medication") == "DRUG"
    assert map_candidate_label("d4data/biomedical-ner-all", "Sign_symptom") == "ADR"
    assert map_candidate_label("d4data/biomedical-ner-all", "Date") is None


def test_exact_span_metrics_penalize_boundary_errors():
    metrics = exact_span_metrics(
        [(0, 9, "DRUG"), (29, 39, "ADR")],
        [(0, 8, "DRUG"), (29, 39, "ADR")],
    )

    assert metrics["true_positive"] == 1
    assert metrics["false_positive"] == 1
    assert metrics["false_negative"] == 1
    assert metrics["f1"] == pytest.approx(0.5)


def test_gold_validation_requires_frozen_labels_and_exact_offsets():
    row = {
        "sample_id": "NER0001",
        "review_status": "complete",
        "sentence": "Clozapine may cause neutropenia.",
        "gold_entities_json": '[{"text":"Clozapine","label":"DRUG","start":0,"end":9}]',
    }

    assert load_and_validate_gold([row])[0]["gold_spans"] == {(0, 9, "DRUG")}
    with pytest.raises(ValueError, match="review_status must be complete"):
        load_and_validate_gold([{**row, "review_status": "pending"}])
    with pytest.raises(ValueError, match="span text does not match offsets"):
        load_and_validate_gold(
            [
                {
                    **row,
                    "gold_entities_json": '[{"text":"clozapine","label":"DRUG","start":0,"end":9}]',
                }
            ]
        )
