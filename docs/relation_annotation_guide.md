# Relation annotation pilot

## Unit and labels

The unit is a unique normalized drug–ADR text pair within one sampled sentence.
Repeated mentions of the same drug or event string in one sentence are folded
into one pair record. Every candidate retains its sample ID, PMID, full evidence
sentence, source stratum, baseline prediction, and cue spans.

Assign one label:

- `supported`: the sentence presents the drug and event as related in an
  adverse-event, risk, clinical monitoring, or reported-outcome context. This
  does not mean the text proves causality.
- `negated`: the sentence explicitly denies or rules out the drug–event link.
- `speculative`: the sentence presents a possible, hypothesized, or uncertain
  drug–event link.
- `co_mention`: both are present, but the sentence does not present them as an
  adverse-event relation. This includes treatment of an event with a drug and
  links between an unrelated drug/event pair in a multi-entity sentence.
- `unclear`: the sentence alone does not support a reliable decision. Exclude
  this label from the headline metric and report its count.

The evaluation's binary “relation mention” task treats `supported`, `negated`,
and `speculative` as a relation being discussed; `co_mention` is the negative
class. Four-way status metrics retain the distinction among relation context
labels. These are sentence-level labels, not clinical causality judgments.

## Sampling and provenance

The pilot uses only sentences from the existing reviewed NER sample: 80
`random_article` rows and 40 `target_enriched` rows. Pair candidates are formed
from the reviewed NER spans. The resulting 117 unique surface-form pairs come
from 59 PMIDs: 33 pairs in the random stratum and 84 in the enriched stratum.
Pairs from the same sentence are correlated, and the enriched stratum is not a
prevalence sample. Keep the strata separate; do not interpret a pooled score as
a population estimate.

The labels in the current pilot are an **assistant-curated first pass**, not
independent human gold annotations or an adjudicated reference set. They were
assigned after the first baseline existed, and the cue rules were then revised
using errors in this same sample. This creates annotator and direct
development-set bias. Current metrics are in-sample diagnostics only. An
independent human curator must review and adjudicate labels, and a separate
PMID-disjoint holdout must be created before any performance claim is used in a
report or presentation.

## Reproduce

```bash
python scripts/prepare_relation_annotation.py
python scripts/run_relation_evaluation.py
```

`data/annotated/relation_annotation_sample.csv` contains each pair, label,
prediction, evidence sentence, and prediction cues. The generator stores the
current first-pass labels in `scripts/prepare_relation_annotation.py` so the
pilot can be reproduced. `results/evaluation/relation_metrics.json` contains
the metric definitions and per-stratum figures. The error table is
`results/evaluation/relation_error_analysis.csv`.

## Current exploratory results

The pair-scoped rule baseline was measured on 107 non-unclear pair labels; 10
of 117 were excluded as unclear. Relation-mention detection across both
strata combined had precision 0.894, recall 0.663, and F1 0.761. Four-way
status accuracy was 0.636. Keep strata separate: random-article P/R/F1 were
0.850/0.773/0.810 (29 pairs), and target-enriched P/R/F1 were
0.913/0.627/0.743 (78 pairs). These are post-refinement development scores,
not held-out validation results.

These values are not validated model performance because the labels are not
independent human gold and multiple pair records share a sentence. The main
remaining errors are missed `supported` pairs (29 predicted as co-mention) and
false relation calls on co-mentions (7 predicted as supported). Speculation
recall on this pilot was 13/13, but only 13 examples were labeled speculative.
These counts describe this development sample only.
