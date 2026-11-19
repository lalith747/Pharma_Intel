from pharmaintel.evaluation.annotation import (
    build_corpus_relevance_review,
    find_exact_occurrences,
    make_annotation_entity,
    sample_annotation_sentences,
)


def test_relevance_review_flags_exact_terms_without_claiming_relevance():
    rows = build_corpus_relevance_review(
        [
            {
                "pmid": "1",
                "title": "Clozapine-associated neutropenia",
                "abstract": "A report on clozapine.",
            }
        ],
        query="clozapine AND neutropenia",
    )

    assert rows[0]["drug_term_in_title"] is True
    assert rows[0]["adr_term_in_title"] is True
    assert rows[0]["drug_term_in_abstract"] is True
    assert rows[0]["adr_term_in_abstract"] is False
    assert rows[0]["manual_relevance"] == ""


def test_annotation_sample_is_deterministic_and_strata_are_separate():
    sentences = [
        {"pmid": "1", "sentence_index": "1", "sentence": "Clozapine may cause neutropenia."},
        {"pmid": "1", "sentence_index": "2", "sentence": "The patient recovered."},
        {"pmid": "2", "sentence_index": "1", "sentence": "Risperidone was administered."},
        {"pmid": "3", "sentence_index": "1", "sentence": "Neutropenia was reported."},
    ]

    sample_a = sample_annotation_sentences(
        sentences, {}, random_article_count=1, enriched_article_count=1, seed=11
    )
    sample_b = sample_annotation_sentences(
        sentences, {}, random_article_count=1, enriched_article_count=1, seed=11
    )

    assert sample_a == sample_b
    assert len(sample_a) == 2
    assert {row["sampling_stratum"] for row in sample_a} == {
        "random_article",
        "target_enriched",
    }
    assert sample_a[1]["gold_entities_json"] == ""
    assert all(row["review_status"] == "pending" for row in sample_a)


def test_annotation_helper_resolves_case_insensitive_exact_occurrences():
    sentence = "Clozapine was stopped; clozapine was later restarted."

    assert find_exact_occurrences(sentence, "clozapine") == [(0, 9), (23, 32)]
    assert make_annotation_entity(sentence, "clozapine", "DRUG", 1) == {
        "text": "clozapine",
        "label": "DRUG",
        "start": 23,
        "end": 32,
    }
