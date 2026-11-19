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

## Current corpus run

The current run scanned 3,915 sentence rows from 385 PMIDs, created 901
sentence-pair evidence records, and ranked five distinct clozapine/event terms.
The top row is clozapine–neutropenia with 127 unique PMIDs, 125 positive
PMIDs, two negative-only PMIDs, consistency 0.906, and score 4.379. These are
counts from the retrieved literature snapshot and rule baseline, not clinical
risk estimates.

| Rank | Event term as extracted | Unique PMIDs | Positive PMIDs | Negated-only PMIDs | Consistency | Score |
|---:|---|---:|---:|---:|---:|---:|
| 1 | neutropenia | 127 | 125 | 2 | 0.906 | 4.379 |
| 2 | agranulocytosis | 66 | 66 | 0 | 0.939 | 3.950 |
| 3 | leukopenia | 10 | 10 | 0 | 0.950 | 2.278 |
| 4 | granulocytopenia | 4 | 4 | 0 | 1.000 | 1.609 |
| 5 | neutropenic | 2 | 2 | 0 | 0.750 | 0.824 |

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
