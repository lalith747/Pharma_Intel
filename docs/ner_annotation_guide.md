# PharmaIntel NER annotation guide (draft v1)

## Purpose and scope

This annotation set is for a first-pass benchmark of drug and adverse-event mention extraction from PubMed abstracts. Entity recognition is independent of whether an event is caused by a drug. Annotate an event mention even when the sentence negates, questions, or speculates about the relationship; relation and assertion labels are handled separately later.

## Labels

- `DRUG`: a named medicinal active ingredient, combination, or branded medicinal product. Annotate the shortest complete drug name. Do not label a general pharmacological class (for example, “antipsychotics”) unless it is a specific product name.
- `ADR`: a specific adverse health outcome, including a symptom, diagnosis, or laboratory abnormality discussed as an adverse event. Do not label the underlying indication (for example, schizophrenia) merely because it appears in the abstract. If the sentence and title do not make the event status clear, leave the entity out and explain the uncertainty in notes.

For this case study, retain the source terms exactly. `neutropenia`, `agranulocytosis`, `granulocytopenia`, `leukopenia`, and `leucopenia` are separate annotated surface forms; do not normalize them into one label during annotation.

## Span policy

1. Mark every occurrence in the sampled sentence, including repeated mentions.
2. Use exact character offsets in the sentence: `start` is zero-based and inclusive; `end` is exclusive. The slice `sentence[start:end]` must equal `text` exactly.
3. Include the complete multiword entity, but omit surrounding punctuation and determiners.
4. Annotate generic and brand drug names when they refer to a medicinal product. Do not infer an omitted drug or event from another sentence.
5. If a mention could be either a drug or an ADR under these definitions, do not guess; use `annotator_notes` and mark the row `needs_adjudication`.

## CSV annotation format

`gold_entities_json` contains the finalized spans. Use `[]` when a sentence has no entities. Example:

```json
[{"text":"Clozapine","label":"DRUG","start":0,"end":9},{"text":"neutropenia","label":"ADR","start":34,"end":45}]
```

Set `review_status` to `complete` when the spans are final, or `needs_adjudication` when another review is needed. Do not edit `sentence`, `PMID`, sample ID, or sampling stratum.

The Streamlit annotation screen can add spans by matching the exact mention text to the sentence, including selecting among repeated occurrences. It writes directly to the local CSV. Start it from the project root with `streamlit run dashboard/annotation_app.py`.

## Sampling and interpretation

The generated sample has two strata. `random_article` selects one sentence from each randomly selected paper and is the only stratum for an initial aggregate estimate. `target_enriched` deliberately selects sentences containing a clozapine alias and a target blood-event term; report these separately as a challenge set. This small article-balanced sample is not a prevalence-representative sample of all PubMed sentences. Freeze annotations before calculating model metrics and record any adjudication.
