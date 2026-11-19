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
assigned from the sentence text after the baseline had been written. This
creates annotator and development-set bias. The scores below are exploratory
error-analysis signals only. An independent human curator must review and
adjudicate the labels before any performance claim is used in a report or
presentation.

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

The rule baseline was evaluated on 107 non-unclear pair labels; 10 of 117 were
excluded as unclear. Relation-mention detection across the two strata combined
had precision 0.833, recall 0.506, and F1 0.629. The four-way status accuracy
was 0.505. Keep the strata separate: random-article P/R/F1 were
0.750/0.682/0.714 (29 pairs), and target-enriched P/R/F1 were
0.882/0.448/0.594 (78 pairs).

These values are not validated model performance because the labels are not
independent human gold and multiple pair records share a sentence. The most
common pilot errors were missed relation wording (33 `supported` pairs and 10
`speculative` pairs were predicted as co-mention) and sentence-level cue spill
(9 co-mention pairs were assigned a relation cue elsewhere in the sentence).
This confirms that cue presence must eventually be scoped to the individual
drug–event pair and clause.
