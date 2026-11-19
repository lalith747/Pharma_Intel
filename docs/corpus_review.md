# PubMed corpus review — clozapine and neutropenia

**Retrieval date:** 2026-11-19 (UTC)  
**Search:** `"clozapine"[Title/Abstract] AND "neutropenia"[Title/Abstract]`  
**Source:** PubMed through NCBI E-utilities

## Retrieval snapshot

| Check | Result |
|---|---:|
| PubMed search matches | 459 |
| Records fetched and deduplicated | 459 |
| Journal article records | 458 |
| PubMed Bookshelf records | 1 |
| Records with abstracts | 385 |
| Records without abstracts | 74 |
| Abstract sentence rows | 3,916 |
| PMIDs not fetched | 0 |

The Bookshelf citation is PMID 33074616, *Clozapine Initiation for Schizophrenia: A Review of Clinical Effectiveness and Guidelines*. The fetcher now retains PubMed Bookshelf records as well as journal articles. The local metadata and records preserve `record_type` to make this distinction visible.

## Search relevance review

The query is a **broad retrieval set**, not a manually screened set of evidence for clozapine-caused neutropenia. The title/abstract query can retrieve papers focused on another medication that mention clozapine and neutropenia in background or comparisons. A keyword match is not a relation label. The search can also include reviews, guidelines, and Bookshelf content in addition to primary studies.

The generated lexical audit counts clozapine aliases and blood-event terms separately in titles and abstracts. Those flags help prioritize review; they do not determine inclusion. `data/processed/pubmed/corpus_relevance_review.csv` has a blank `manual_relevance` field for `relevant`, `irrelevant`, or `uncertain`, plus reviewer notes. The abstract is not included in this sheet to keep it compact; use the same PMID in `data/raw/pubmed/pubmed_records.jsonl` for context.

Suggested inclusion decision: retain a citation in the case-study evidence set when clozapine is substantively discussed in connection with neutropenia or a clearly identified related hematological event. Mark as irrelevant when the terms are unrelated background co-mentions. Mark uncertain when the abstract alone does not establish the paper's focus; do not infer causality from inclusion.

## NER annotation sample

`data/annotated/ner_annotation_sample.csv` contains 120 sentences selected with seed `20261119`. The finalized annotation set contains 234 entity spans in `gold_entities_json`. It excludes ambiguous abbreviations, generic outcomes, baseline conditions, and unrelated diseases.

- **80 `random_article` rows:** one sentence from each randomly sampled paper. This article-balanced stratum is the initial evaluation sample.
- **40 `target_enriched` rows:** one sentence from each distinct paper containing a clozapine alias and one target blood-event term. Treat this separately as a challenge/error-analysis set, not as part of the aggregate estimate.

Follow [the annotation guide](ner_annotation_guide.md) to review and correct spans if needed; use `[]` for a sentence with no entities. Keep the random and enriched strata separate when reporting results.

To regenerate the review sheets from the current raw/processed corpus:

```bash
python scripts/prepare_ner_annotation.py
```

Search counts change over time. Preserve each retrieval's metadata and treat this snapshot as a dated corpus version. For future NCBI requests, set `NCBI_EMAIL` to a contact address as described in the setup instructions.
