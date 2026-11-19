# PharmaIntel-AI project plan

## Research question

Can a biomedical NLP pipeline extract drug–adverse-event evidence from PubMed and organize it into traceable, ranked safety signals?

## Initial case study and terminology

- Drug: clozapine
- Primary event term: neutropenia
- Assignment 1: clozapine–neutropenia, 929 reports; clozapine–agranulocytosis, 244 reports; clozapine–granulocytopenia, 5 reports.
- Assignment 2: clozapine–neutropenia, EBGM 50.81.
- Preserve each source outcome as recorded. If related outcomes are aggregated into an exploratory event family, make the mapping explicit, versioned, and reversible.

## Project components and phases

1. **Architecture and environment:** establish reproducible project structure and compute constraints.
2. **PubMed retrieval (initial implementation complete):** the CLI searches PubMed, fetches records, preserves PMIDs and normalized abstracts, deduplicates by PMID, sentence-splits abstracts, and saves JSONL/CSV plus query metadata. Next, review and refine the search strategy and inclusion rules before expanding the corpus.
3. **Model inventory and benchmarking (first NER benchmark complete):** the 120-row annotation set, strict exact-span evaluator, and benchmark runner were used to compare the lexical baseline, BC5CDR BiomedBERT, and Biomedical NER All. Select BC5CDR BiomedBERT as the transformer baseline; retain the lexical baseline for comparison. See `docs/ner_benchmark_results.md`. Inspect any additional candidate model's architecture, intended task, input format, output labels, license, and resource requirements before adding it.
4. **Preprocessing:** deduplicate, preserve relevant context, split into sentences, and retain links to source abstracts.
5. **Drug NER and ADR NER:** implement transformer-based extraction and compare with a transparent rule-based baseline.
6. **Relation extraction and context baseline (development implementation complete):** pair-scoped cue assignment preserves pair evidence and offsets and reports assertion cues separately. It remains a lexical heuristic and does not infer causality.
7. **Evaluation (development pilot complete):** 117 pair labels and separate-stratum diagnostics are generated. Labels are assistant-curated and the cue rules were revised using this sample's errors. Independent human adjudication and a PMID-disjoint holdout are required before performance claims. See `docs/relation_annotation_guide.md`.
8. **Evidence prioritization (prototype complete):** rank the local PubMed case-study corpus using unique-PMID support and assertion consistency. The score is a triage aid, not a causal estimate. See `docs/signal_prioritization.md`.
9. **Knowledge graph (prototype complete):** export traceable GraphML with drug, event, evidence sentence, and publication nodes.
10. **Dashboard:** build a Streamlit + Plotly experience for model comparison, evidence inspection, evaluation, ranking, and graph exploration.
11. **Deliverables:** notebook, ranked CSV, 2–3 page PDF report, reproducibility instructions, and GitHub repository.
12. **Optional extension:** SocialPulse for social-media ADR mining, only after data access and model validity are addressed.

## Scientific safeguards

- Co-occurrence and semantic similarity do not establish causality.
- Model confidence is not the probability that a drug caused an event.
- PubMed publication counts are not incidence estimates.
- Do not fabricate performance metrics; report evaluation only against a defined annotated sample.
- Retain PMIDs, exact evidence sentences, model/version metadata, and scoring components.
- Do not commit credentials, raw datasets, or private patient data.

## Relation/context baseline status

The current implementation is documented in `docs/relation_extraction_baseline.md`.
It creates records only for same-sentence DRUG × ADR pairs, assigns relation
cues to the closest pair interval within a clause, and keeps
negation/speculation labels and cue spans separate from relation wording. This
remains an unvalidated lexical heuristic, and a relation cue is not proof that
the two mentions are related.

The current development evaluation uses the reviewed NER sample, so it is not
PMID-disjoint from NER development. Pair labels were assigned by this assistant
as a first pass, and cue rules were revised from the pilot errors. Do not
present the current metrics as held-out performance; the saved error analysis
is a diagnostic for preparing an independently adjudicated relation benchmark.

## Assignment deliverables

- Documented Jupyter/Colab notebook
- CSV of extracted and ranked drug–ADR pairs
- 2–3 page PDF report covering methods, results, and discussion
- Interactive dashboard as an additional demonstration goal
