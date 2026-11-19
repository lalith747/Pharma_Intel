# PharmaIntel-AI

**AI-powered pharmacovigilance intelligence from biomedical literature.**

PharmaIntel-AI is a research and portfolio project for retrieving PubMed literature, extracting drug and adverse-event mentions, analysing their sentence-level relationships, and prioritizing traceable evidence for review. It is a literature-mining aid; it does not establish clinical causality or replace pharmacovigilance review.

## Case study

The initial case study is **clozapine–neutropenia**, selected because it is present in both supplied FAERS assignments. Assignment 1 lists 929 reports for neutropenia, alongside separate rows for agranulocytosis (244) and granulocytopenia (5). Assignment 2 reports EBGM 50.81 for clozapine–neutropenia. These are separate source terms and outcomes. Any grouping into a broader hematological event family will be documented as a terminology mapping, not treated as equivalence. FAERS counts are reporting statistics, not incidence or causal estimates.

## Project components

| Component | Planned work |
|---|---|
| Data acquisition | Implemented: PubMed retrieval with PMID-level provenance and reproducible search metadata |
| Biomedical NLP | NER benchmark completed; BC5CDR BiomedBERT selected as the transformer baseline |
| Drug NER | Transformer-based extraction plus an interpretable rule-based baseline |
| ADR NER | Transformer-based adverse-event extraction plus baseline comparison |
| Relation extraction | Verify a model's task, labels, inputs, and domain before using it to classify drug–ADR evidence |
| Context analysis | Detect negation, speculation, uncertainty, and unclear co-mentions |
| Evaluation | Manually annotated sample, precision/recall/F1, and error analysis |
| Signal prioritization | Transparent evidence scoring with traceable supporting sentences and PMIDs |
| Knowledge graph | Connect drugs, adverse events, papers, and evidence relationships |
| Dashboard | Streamlit and Plotly evidence explorer, evaluation views, rankings, and interactive graph |
| SocialPulse | Optional social-media ADR mining extension, subject to data access and validation |
| Deliverables | Notebook, ranked CSV, 2–3 page PDF report, and GitHub repository |

## Development sequence

1. Architecture and environment
2. PubMed retrieval and provenance
3. Model inventory and benchmarking (architecture, input format, output labels, licensing, compute needs)
4. Drug and ADR entity extraction, comparing transformer outputs to rule-based baselines
5. Drug–ADR relationship extraction and context analysis
6. Manual annotation, quantitative evaluation, and error analysis
7. Evidence-level traceability and transparent signal ranking
8. Knowledge graph
9. Streamlit + Plotly dashboard
10. Final notebook, CSV, report, documentation, and repository publication

We will not call keyword matching a complete NLP system. Rules are a baseline to measure against; the transformer and relation-model choices remain open until their intended task and practical requirements are verified. Model confidence is not a causal probability. SocialPulse is an optional extension after the primary literature pipeline is working and evaluated.

## Development environment

The project targets Python 3.10–3.12. Create an isolated environment and install the project dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[all]"
```

Install PyTorch separately so CPU-only machines do not accidentally download CUDA libraries. For the current Ubuntu CPU setup:

```bash
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

For another platform or an NVIDIA GPU, use the appropriate command from the [official PyTorch installation selector](https://pytorch.org/get-started/locally/). The `requirements.txt` file installs the project extras; install the matching PyTorch build as a separate platform-specific step. Model weights are downloaded from Hugging Face when a selected model is first used and are not stored in the repository.

The current development machine is Ubuntu 22.04, Python 3.10, Intel Core i7-13700, 16 GB RAM, and no NVIDIA GPU. CPU inference is the initial target; latency and memory use must be measured before selecting models.

## Retrieve the initial PubMed sample

Set a contact email for NCBI and run the default clozapine–neutropenia search:

```bash
export NCBI_EMAIL="your-email@example.org"
python -m pharmaintel.data_acquisition.pubmed --max-results 100
```

The command writes normalized source records and retrieval metadata to `data/raw/pubmed/`, plus a records CSV and sentence-level CSV to `data/processed/pubmed/`. PMID, title, publication details, query, and retrieval time are retained so each sentence can be traced to its source. Raw and processed data directories are git-ignored. The query and result limit can be changed with `--query` and `--max-results`; PubMed's relevance ordering is the default.

The sentence splitter is a deterministic rule baseline with common abbreviation guards. It is intended to prepare reviewable sentences for later biomedical NLP, not as a validated sentence-boundary model.

The current dated retrieval snapshot and relevance caveats are in [the corpus review](docs/corpus_review.md). To create the review and annotation CSVs, run:

```bash
python scripts/prepare_ner_annotation.py
```

Use the local annotation screen to label the sample sentence by sentence:

```bash
streamlit run dashboard/annotation_app.py
```

The screen lets you inspect and correct spans in `gold_entities_json` in `data/annotated/ner_annotation_sample.csv`. Candidate model predictions stay hidden. Read [the NER annotation guide](docs/ner_annotation_guide.md) before starting. The random and target-enriched strata must remain separate.

After every row has a reviewed JSON annotation and `review_status` is `complete`, run the benchmark:

```bash
python scripts/run_ner_benchmark.py
```

This runs the target-term lexical baseline and the two shortlisted Hugging Face token-classification models, then writes strict exact-span metrics separately for each sampling stratum. The target-term baseline is intentionally narrow, and the models' Chemical/Disease or broad biomedical labels are mapped to the project's DRUG/ADR targets only for comparison; original labels and model revisions are retained in provenance. Model outputs and confidence scores are not causal evidence.

The first completed benchmark and model-selection rationale are in [NER benchmark results](docs/ner_benchmark_results.md).

## Current implementation status

The repository scaffold, package metadata, development environment, project plan, model research shortlist, PubMed corpus snapshot, annotation screen, and sample are in place. PubMed search/fetch supports journal and Bookshelf records, PMID deduplication, sentence splitting, and provenance-preserving CSV/JSONL outputs. The NER benchmark runner, target-term rule baseline, exact-span evaluator, and first model benchmark are complete. Relation extraction, signal ranking, knowledge graph, and main research dashboard remain planned work.

## Repository layout

```text
.
├── data/{raw,processed,annotated}/   # local data; files are git-ignored
├── dashboard/                        # Streamlit application
├── docs/                              # research plan and methods notes
├── notebooks/                         # assignment and exploratory notebooks
├── results/{figures,evaluation}/      # generated outputs; data files are ignored
├── src/pharmaintel/                  # installable pipeline package
└── tests/                             # automated checks
```

