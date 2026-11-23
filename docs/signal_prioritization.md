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

## Cross-source index audit

The dashboard reports a 0–100 **exploratory cross-source index** for the exact
clozapine–neutropenia pair only. It uses Assignment 2 EBGM (50.81) and the
current literature corpus. The Assignment 1 count (929) is displayed as context
but does not enter the numeric index. The values 929 and 50.81 are assignment-
provided inputs; this project has not independently regenerated them from raw
FAERS data.

| Component | Transform | Weight |
|---|---|---:|
| FAERS EBGM | EBGM / (1 + EBGM) | 0.30 |
| Literature breadth | 1 − exp(−unique PMIDs / 50) | 0.25 |
| Supported-relation share | supported PMIDs / all relation PMIDs | 0.25 |
| Assertion consistency | current literature score consistency | 0.20 |

The final index is 100 × the weighted sum. The saturation constant and weights
are exploratory choices, not parameters estimated against expert labels or
outcomes. No FAERS values are imputed for other ADR terms; those terms remain
ranked by the literature-only score. It is deliberately called an index, not a
confidence score.

### Reproducibility and sensitivity results

Run the reproducible audit with:

```bash
python scripts/audit_cross_source_index.py
```

The audit checks that the PMID status counts reconcile, recomputes assertion
consistency, recomputes the weighted index, and evaluates weight sensitivity.
For the bundled snapshot:

| Audit | Result |
|---|---:|
| Unique PMID status counts | 93 supported + 18 speculative + 5 negated + 3 mixed = 119 |
| Recomputed assertion consistency | 0.8697; matches the stored value |
| Recomputed index | 89.040; dashboard displays 89.0 |
| Equal weights | 88.485 |
| Omit one component, then renormalize remaining weights | 85.170–92.670 |
| Allow any nonnegative weights summing to one | 78.151–98.070 |
| Hold EBGM weight at 30%, redistribute the remaining 70% | 84.127–92.942 |

This confirms the arithmetic and exposes its dependence on subjective weights.
It does **not** validate ranking quality, calibration, clinical meaning, or
causality. The full-weight range is wide because the component values themselves
range from 0.782 to 0.981. EBGM transforms to 0.981 under `EBGM/(1+EBGM)`, so
this transform is near its ceiling for 50.81. Three of four components use the
same literature evidence and should not be treated as independent evidence.

No criterion validation is possible yet: the cross-source score exists for one
pair only, there are no independent expert labels or outcome data, and the
blinded relation holdout has 60 pending annotations. The available relation
pilot used assistant-curated in-sample labels and rules revised against their
errors; in that pilot, supported-relation recall was 0.581 and co-mention
precision was 0.268. Those are development diagnostics, not independent
performance estimates. Consequently, 89.0 is a reproducible exploratory index,
not a validated score. The audit output is saved to
`results/evaluation/cross_source_index_audit.json`.

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
