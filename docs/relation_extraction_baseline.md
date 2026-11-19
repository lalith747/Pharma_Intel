# Sentence-level relation and assertion baseline

## What it does

`pharmaintel.relation_extraction.extract_sentence_relations` combines drug and
ADR mentions in a sentence and returns one evidence record for every in-sentence
pair. It can use the clozapine case-study lexicon or accept spans from the
Hugging Face NER pipeline. Each record retains the exact sentence, mention
offsets, relation cue text and offsets, assertion cues, method, and a separate
flag for explicit causal wording.

The baseline reports two pair-specific evidence classes:

- `explicit_relation_language`: at least one relation cue is assigned to this pair by the nearest-span heuristic.
- `co_mention_only`: both entities occur, but none of the current relation cues appear.

Assertion context is reported separately as `affirmed_or_unmarked`, `negated`,
or `speculative`. These labels describe lexical cues detected by the baseline;
they do not establish truth, clinical causality, or a causal probability.
`causal_language` only indicates that wording such as “caused” or “induced” was
present. `causal_conclusion` intentionally remains null.

## Current cue baseline

Relation cues include association/link wording (including `linked to`), risk
wording, event-after-exposure wording (including `reported with`), common onset
verbs, and adverse-effect wording. Causal wording already includes `trigger*`,
`resulted in`, `induced`, and `caused`. These examples are covered by the current
baseline; adding duplicate patterns would not address the observed errors.
Negation and speculation use explicit cue lists. A cue is considered local when it occurs
assigned to the closest drug–ADR mention interval in a punctuation-delimited
clause, based on distance and span length. Ties are left unassigned. Negation
and speculation still use an 80-character window around the pair's mentions.
These are inspectable heuristics: they can miss coordinated event mentions,
long-distance scope, and ambiguous or reported speech. They do not perform
syntactic parsing.

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
exploratory 117-pair development pilot and its limitations are described in
`docs/relation_annotation_guide.md`. Its labels were assigned by an assistant
and the cues were refined on the same sample. The next evaluation milestone is
independent human adjudication on a PMID-disjoint sample, with random and
target-enriched strata reported separately. Only then should a transformer
relation model be considered, after its task, input format, labels, training
data, licensing, and compute needs are verified. The ADE sentence classifier
in the model inventory is not pair-aware and must not be substituted for this
task.
