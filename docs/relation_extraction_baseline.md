# Sentence-level relation and assertion baseline

## What it does

`pharmaintel.relation_extraction.extract_sentence_relations` combines drug and
ADR mentions in a sentence and returns one evidence record for every in-sentence
pair. It can use the clozapine case-study lexicon or accept spans from the
Hugging Face NER pipeline. Each record retains the exact sentence, mention
offsets, relation cue text and offsets, assertion cues, method, and a separate
flag for explicit causal wording.

The baseline reports two evidence classes:

- `explicit_relation_language`: at least one relation cue occurs in the sentence.
- `co_mention_only`: both entities occur, but none of the current relation cues appear.

Assertion context is reported separately as `affirmed_or_unmarked`, `negated`,
or `speculative`. These labels describe lexical cues detected by the baseline;
they do not establish truth, clinical causality, or a causal probability.
`causal_language` only indicates that wording such as “caused” or “induced” was
present. `causal_conclusion` intentionally remains null.

## Current cue baseline

Relation cues include association/link wording, risk wording, event-after-
exposure wording, common onset verbs, and adverse-effect wording. Negation and
speculation use explicit cue lists. A cue is considered local when it occurs
within 80 characters of a supplied entity span. This window is a simple,
inspectable heuristic: it can cross clause boundaries, miss long-distance
scope, and misclassify ambiguous or reported speech. A sentence-level cue may
also be unrelated to one of several drug–ADR pairs in that sentence.

When NER spans are supplied, only mapped DRUG and ADR labels are considered.
Otherwise, the function can use the case-study lexicon for clozapine and the
selected blood-cell event terms. The lexical mode is intentionally not general
biomedical NER.

## Use

```python
from pharmaintel.relation_extraction import extract_sentence_relations

records = extract_sentence_relations(
    "Neutropenia was reported following clozapine treatment."
)
```

## Validation required before interpretation

This is a rule-based research baseline, not a validated relation model. An
exploratory 117-pair pilot and its limitations are described in
`docs/relation_annotation_guide.md`. The labels were assigned by an assistant
as a first pass, so the metrics are error-analysis signals rather than
independent human-gold performance. The next evaluation milestone is
independent human adjudication on a PMID-disjoint sample, with random and
target-enriched strata reported separately. Only then should a transformer
relation model be considered, after its task, input format, labels, training
data, licensing, and compute needs are verified. The ADE sentence classifier
in the model inventory is not pair-aware and must not be substituted for this
task.
