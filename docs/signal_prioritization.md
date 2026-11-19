# Case-study signal prioritization

## Scope

`scripts/run_corpus_intelligence.py` applies the clozapine case-study lexicon
and pair-scoped relation baseline to every sentence in the local PubMed
sentence corpus. The current snapshot has 3,915 sentence rows from 385 PMIDs
with abstracts. The original PubMed retrieval contained 459 records, including
74 records without abstracts; those records cannot contribute sentence-level
evidence.

The lexicon canonicalizes the clozapine brand aliases Clozaril and Leponex to
the drug key `clozapine`. It preserves ADR surface terms as distinct strings;
for example, `neutropenia`, `neutropenic`, and `granulocytopenia` are not
silently merged. The retrieval query is broad and was not manually screened
for relevance, so co-mentions and irrelevant articles remain possible.

## Scoring formula

First, relation evidence is collapsed to one status per PMID and normalized
drug–ADR pair. Multiple sentences in one PMID do not increase paper frequency.
When a paper contains both positive and negated relation evidence, it is marked
`mixed` rather than allowing repeated sentences to dominate.

- `supported`: weight 1.0 for assertion consistency.
- `speculative`: weight 0.5.
- `negated`: weight 0.
- `mixed`: weight 0.5.
- `co_mention`: excluded from scoring.

Let `P` be unique PMIDs with supported, speculative, or mixed evidence, and
`A` be unique PMIDs with any explicit relation assertion. Then:

```text
consistency = (supported_PMIDs + 0.5 × speculative_PMIDs + 0.5 × mixed_PMIDs) / A
frequency_component = ln(1 + P)
priority_score = frequency_component × consistency
```

This score is a transparent queue for literature review. It is not a model
confidence, causal probability, incidence estimate, effect size, or validated
signal. PMIDs may also report overlapping cohorts, and the cue baseline can
still miss or misassign relations.

## Exploratory cross-source profile

The dashboard additionally reports a 0–100 **exploratory cross-source index**
for the exact clozapine–neutropenia pair only. It uses the Assignment 1 report
count (929) and Assignment 2 EBGM (50.81), together with the current literature
corpus. This is a fixed, hand-designed weighted summary; it is not a trained
machine-learning model, a calibrated confidence estimate, an incidence rate,
or a causal probability. It must not be interpreted clinically.

| Component | Transform | Weight |
|---|---|---:|
| FAERS EBGM | EBGM / (1 + EBGM) | 0.30 |
| Literature breadth | 1 − exp(−unique PMIDs / 50) | 0.25 |
| Supported-relation share | supported PMIDs / all relation PMIDs | 0.25 |
| Assertion consistency | current literature score consistency | 0.20 |

The final index is 100 × the weighted sum. The saturation constant and weights
are exploratory choices, not parameters estimated against expert labels or
outcomes. No FAERS values are imputed for other ADR terms; those terms remain
ranked by the literature-only score. A validated composite needs independent
expert labels, a prespecified calibration/validation protocol, and uncertainty
analysis. It is deliberately called an index, not a confidence score.

## Current transformer corpus run

The pinned BC5CDR model scanned 3,915 sentence rows from 385 PMIDs, created
1,148 case-study candidate pair rows, and ranked five extracted blood-event
terms. In the current snapshot, clozapine–neutropenia has 119 unique PMIDs,
114 positive PMIDs, consistency 0.870, and literature score 4.127. Values can
change when the retrieved corpus or model output changes. These counts describe
this literature snapshot, not clinical risk.

| Rank | Event term as extracted | Unique PMIDs | Positive PMIDs | Negated-only PMIDs | Consistency | Score |
|---:|---|---:|---:|---:|---:|---:|
| 1 | neutropenia | 119 | 114 | 5 negated-only | 0.870 | 4.127 |
| 2 | agranulocytosis | 65 | 65 | 0 | 0.931 | 3.900 |
| 3 | leukopenia | 6 | 6 | 0 | 1.000 | 1.946 |
| 4 | granulocytopenia | 4 | 4 | 0 | 1.000 | 1.609 |
| 5 | neutropenic | 1 | 1 | 0 | 0.500 | 0.347 |

The CSV keeps component counts and its calculation method. Sentence-level
evidence stays in the local processed-data directory and retains PMID, title,
sentence index, exact sentence, cues, and context status.

## Outputs and verification

Run:

```bash
python scripts/run_corpus_intelligence.py
```

Outputs:

- `results/ranked_signals.csv` — ranked aggregate with score components.
- `data/processed/pubmed/relation_evidence.csv` — local evidence rows with PMIDs and sentences.
- `results/evaluation/corpus_relation_summary.json` — retrieval size, evidence/status counts, and method metadata.
- `results/pharmaintel_evidence_graph.graphml` — traceable evidence graph.

The graph has separate drug, event, evidence, and publication nodes. Each
evidence node links to its drug, ADR, and source PMID and stores the exact
sentence and cues. It contains 901 evidence nodes and 318 publication nodes in
the current run. Every evidence node has three outgoing provenance edges.
