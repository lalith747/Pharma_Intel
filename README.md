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
| Relation extraction | Implemented: pair-scoped rule baseline separating relation language from co-mention |
| Context analysis | Implemented: lexical negation/speculation cues with traceable spans; scope remains unvalidated |
| Evaluation | Manually annotated sample, precision/recall/F1, and error analysis |
| Signal prioritization | Literature triage score plus an explicitly uncalibrated cross-source profile for clozapine–neutropenia (FAERS EBGM + literature evidence) |
| Knowledge graph | Implemented: GraphML evidence graph connecting drugs, ADRs, sentences, and PMIDs |
| Dashboard | Implemented: modular Streamlit pages for overview, signals, evidence, graph, SocialPulse, and methods |
| SocialPulse | FDA Drug Safety Communications archive filtered for clozapine/Clozaril; six-hour cache and optional local sample screen; no paid X API |
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

Keyword/rule matching is treated as a baseline, not a complete NLP system. The selected transformer is used for entity candidates, while relation and assertion decisions currently use a transparent lexical baseline. Model confidence is not a causal probability. SocialPulse shows official FDA Drug Safety Communications that mention clozapine/Clozaril, separately from PubMed and FAERS. It parses the current FDA archive listing; entries older than the page’s archive boundary may require following FDA’s historical archive link. It does not include general news or X posts; official X API reads are pay-per-use. Optional user-supplied social samples require permitted access, de-identification, and human validation before research claims.

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

This acquisition step calls **NCBI PubMed E-utilities** through Biopython. Set `NCBI_EMAIL` to identify the client; `NCBI_API_KEY` is optional. The transformer runs locally with PyTorch after downloading the public, revision-pinned Hugging Face checkpoint. PharmaIntel does not use the OpenAI API or any hosted LLM inference API.

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

## Relation evidence, signal ranking, and knowledge graph

After PubMed retrieval, generate traceable case-study evidence, ranked signal
counts, and a GraphML knowledge graph:

```bash
python scripts/run_corpus_intelligence.py
```

The script scans the local sentence CSV, writes the ranked aggregate to
`results/ranked_signals.csv`, writes the evidence graph to
`results/pharmaintel_evidence_graph.graphml`, and retains PMID-level sentence
evidence locally under `data/processed/pubmed/`. Its score prioritizes
literature-review candidates; it is not a probability or causal estimate. Read
the [scoring method and limitations](docs/signal_prioritization.md) before
interpreting ranks.

## Transformer corpus run and dashboard

The selected BC5CDR token classifier is pinned to a model revision and can run
offline after its Hugging Face snapshot has been cached. It scans the local
sentence corpus and writes NER predictions, pair-level evidence, a case-study
ranking, GraphML, and a provenance/limitations summary:

```bash
python scripts/run_transformer_corpus_ner.py
streamlit run dashboard/app.py
```

BC5CDR outputs `Chemical` and `Disease`, not drug-specific and ADR-specific
classes. The app retains those labels and scores and restricts the primary
case-study ranking to clozapine and a declared blood-event term list. Corpus
metrics are not reported without independent gold annotations.

A PMID-disjoint blinded relation sample and local annotation screen are also
available:

```bash
python scripts/prepare_relation_holdout.py
streamlit run dashboard/relation_annotation_app.py
```

The sample has one candidate pair per PMID, excludes the development PMIDs, and
contains no model predictions. After every row is reviewed and saved, the
gated evaluator can be run with `python scripts/evaluate_relation_holdout.py`.
The resulting metrics are only independent-human validation if the annotations
were completed by a reviewer who did not create the development labels/rules;
the evaluator records this limitation explicitly.

## Notebook and hosting

**Live dashboard:** [PharmaIntel Safety Intelligence](https://pharmaintel.streamlit.app/)

The self-contained, rendered seven-part assignment workflow and caveats are in [`notebooks/01_pharmaintel_pipeline.ipynb`](notebooks/01_pharmaintel_pipeline.ipynb). Saved palette-matched PNG figures are created with `python scripts/build_research_figures.py`. For the hosted results explorer, first regenerate the compressed static outputs and run the app locally:

```bash
python scripts/prepare_dashboard_assets.py
streamlit run dashboard/app.py
```

The same app is deployed from the public GitHub repository to Streamlit Community Cloud with entrypoint `dashboard/app.py`. Alongside precomputed model outputs, it displays a live PubMed literature carousel refreshed through NCBI E-utilities and shared-cached for six hours. SocialPulse reads the free public FDA Drug Safety Communications archive and caches it for six hours; no runtime API credentials are needed. These are source-linked notices, not an automated assessment of causality. See [hosting and API details](docs/deployment.md).

The app uses Streamlit's page navigation with page modules under
`dashboard/pages/` and shared loading/styles in `dashboard/shared.py`. Signal
terms display a within-corpus relative literature index; only the exact
clozapine–neutropenia pair has the supplied FAERS values for the separate,
exploratory cross-source profile.

## Current implementation status

PubMed retrieval, the initial NER benchmark, pair-scoped relation/assertion rules, unique-PMID evidence scoring, and provenance-preserving GraphML are implemented. The dashboard includes an evidence explorer, interactive graph, exploratory cross-source profile, and SocialPulse news feed plus optional screening sandbox. The cross-source index is hand-designed and uncalibrated; it is not a validated confidence score. A pinned BC5CDR model has been run across the 3,915-sentence local snapshot. A 60-record PMID-disjoint sample is prepared, but blinded human review remains pending, so no held-out relation metrics are available. See the [relation methods](docs/relation_extraction_baseline.md), [annotation guide](docs/relation_annotation_guide.md), and [signal prioritization method](docs/signal_prioritization.md).

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

