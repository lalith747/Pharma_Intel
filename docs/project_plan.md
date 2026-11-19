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
6. **Relation extraction:** select an approach only after verifying that its task and label set fit drug–ADR relations; retain the source sentence and prediction details.
7. **Context analysis:** detect negation, speculation, uncertainty, and unclear co-mentions, with explicit limitations.
8. **Evaluation:** manually annotate a defined sample, calculate precision/recall/F1 where appropriate, and review false positives and false negatives.
9. **Evidence prioritization:** score evidence with documented components and preserve evidence-level provenance.
10. **Knowledge graph:** link drugs, events, publications, sentences, and extracted relations.
11. **Dashboard:** build a Streamlit + Plotly experience for model comparison, evidence inspection, evaluation, ranking, and graph exploration.
12. **Deliverables:** notebook, ranked CSV, 2–3 page PDF report, reproducibility instructions, and GitHub repository.
13. **Optional extension:** SocialPulse for social-media ADR mining, only after data access and model validity are addressed.

## Scientific safeguards

- Co-occurrence and semantic similarity do not establish causality.
- Model confidence is not the probability that a drug caused an event.
- PubMed publication counts are not incidence estimates.
- Do not fabricate performance metrics; report evaluation only against a defined annotated sample.
- Retain PMIDs, exact evidence sentences, model/version metadata, and scoring components.
- Do not commit credentials, raw datasets, or private patient data.

## Assignment deliverables

- Documented Jupyter/Colab notebook
- CSV of extracted and ranked drug–ADR pairs
- 2–3 page PDF report covering methods, results, and discussion
- Interactive dashboard as an additional demonstration goal
