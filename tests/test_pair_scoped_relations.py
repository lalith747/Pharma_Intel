from pharmaintel.relation_extraction import extract_sentence_relations


def _entity(sentence: str, text: str, label: str, occurrence: int = 0) -> dict[str, object]:
    start = -1
    for _ in range(occurrence + 1):
        start = sentence.index(text, start + 1)
    return {"text": text, "label": label, "start": start, "end": start + len(text)}


def test_causal_cue_is_scoped_to_the_clozapine_pair():
    sentence = "Previously clozapine-induced neutropenia relapsed after olanzapine treatment."
    entities = [
        _entity(sentence, "clozapine", "DRUG"),
        _entity(sentence, "neutropenia", "ADR"),
        _entity(sentence, "olanzapine", "DRUG"),
    ]

    relations = extract_sentence_relations(sentence, entities)
    by_pair = {(row["drug"]["text"], row["adr"]["text"]): row for row in relations}

    assert by_pair[("clozapine", "neutropenia")]["evidence_class"] == "explicit_relation_language"
    assert by_pair[("clozapine", "neutropenia")]["causal_language"] is True
    assert by_pair[("olanzapine", "neutropenia")]["evidence_class"] == "co_mention_only"
    assert by_pair[("olanzapine", "neutropenia")]["relation_cues"] == []


def test_inflected_cause_and_induce_forms_are_detected():
    sentence = "Clozapine can cause agranulocytosis and is known to induce neutropenia."
    entities = [
        _entity(sentence, "Clozapine", "DRUG"),
        _entity(sentence, "agranulocytosis", "ADR"),
        _entity(sentence, "neutropenia", "ADR"),
    ]

    relations = extract_sentence_relations(sentence, entities)

    assert all(row["evidence_class"] == "explicit_relation_language" for row in relations)
    assert all(row["causal_language"] is True for row in relations)


def test_risk_in_program_name_is_not_a_relation_cue():
    sentence = "The Clozapine Risk Evaluation Strategy monitors patients for neutropenia."
    entities = [
        _entity(sentence, "Clozapine", "DRUG"),
        _entity(sentence, "neutropenia", "ADR"),
    ]

    relation = extract_sentence_relations(sentence, entities)[0]

    assert relation["evidence_class"] == "co_mention_only"
    assert relation["relation_cues"] == []


def test_duplicate_ner_spans_do_not_duplicate_pair_records():
    sentence = "Clozapine can cause neutropenia."
    drug = _entity(sentence, "Clozapine", "DRUG")
    adr = _entity(sentence, "neutropenia", "ADR")

    relations = extract_sentence_relations(sentence, [drug, drug.copy(), adr, adr.copy()])

    assert len(relations) == 1


def test_negated_and_speculative_context_stays_separate_from_causal_conclusion():
    negated = "Neutropenia was not related to clozapine treatment."
    speculative = "Clozapine may cause neutropenia."

    negated_relation = extract_sentence_relations(
        negated,
        [_entity(negated, "clozapine", "DRUG"), _entity(negated, "Neutropenia", "ADR")],
    )[0]
    speculative_relation = extract_sentence_relations(
        speculative,
        [_entity(speculative, "Clozapine", "DRUG"), _entity(speculative, "neutropenia", "ADR")],
    )[0]

    assert negated_relation["assertion"] == "negated"
    assert speculative_relation["assertion"] == "speculative"
    assert negated_relation["causal_conclusion"] is None
    assert speculative_relation["causal_conclusion"] is None
