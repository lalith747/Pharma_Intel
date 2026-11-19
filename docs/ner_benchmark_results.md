# NER benchmark results

**Run date:** 2026-11-19  
**Evaluation:** strict exact-span precision, recall, and F1  
**Annotation set:** 120 PubMed sentences; 80 random article-balanced rows and 40 target-enriched rows

## Results

| System | Stratum | Label | Precision | Recall | F1 | Gold spans |
|---|---|---|---:|---:|---:|---:|
| Case-study lexical baseline | Random article | DRUG | 1.000 | 0.621 | 0.766 | 58 |
| Case-study lexical baseline | Random article | ADR | 0.839 | 0.591 | 0.693 | 44 |
| BC5CDR BiomedBERT | Random article | DRUG | 0.866 | 1.000 | 0.928 | 58 |
| BC5CDR BiomedBERT | Random article | ADR | 0.472 | 0.773 | 0.586 | 44 |
| Biomedical NER All | Random article | DRUG | 0.200 | 0.310 | 0.243 | 58 |
| Biomedical NER All | Random article | ADR | 0.077 | 0.159 | 0.104 | 44 |
| Case-study lexical baseline | Target enriched | DRUG | 1.000 | 0.766 | 0.867 | 47 |
| Case-study lexical baseline | Target enriched | ADR | 0.955 | 0.689 | 0.800 | 61 |
| BC5CDR BiomedBERT | Target enriched | DRUG | 1.000 | 1.000 | 1.000 | 47 |
| BC5CDR BiomedBERT | Target enriched | ADR | 0.822 | 0.984 | 0.896 | 61 |
| Biomedical NER All | Target enriched | DRUG | 0.136 | 0.191 | 0.159 | 47 |
| Biomedical NER All | Target enriched | ADR | 0.096 | 0.148 | 0.116 | 61 |

The random article stratum is the primary result. The target-enriched stratum intentionally contains more clozapine and blood-event mentions, so it is useful for stress testing but must not be pooled with the random estimate.

## Decision

Use `Glasgow-AI4BioMed/bioner_bc5cdr` as the primary transformer baseline for the next pipeline stage. It captured all drug spans in the random sample and recovered more ADR spans than the lexical baseline, although its ADR precision was lower because the checkpoint's broad `Disease` label is mapped to PharmaIntel's narrower ADR target.

Keep the lexical baseline as a transparent comparator. Its dictionary is intentionally focused on the clozapine case study; high precision does not mean that it generalizes to new drugs or events.

Do not use `d4data/biomedical-ner-all` as the primary model for this case study. Its MACCROBAT-trained broad entity labels produced too many mapped false positives in both strata.

## Reproducibility

The full machine-readable artifacts are in `results/evaluation/`:

- `ner_metrics.csv`
- `ner_predictions.jsonl`
- `ner_model_provenance.json`

The run used Python 3.10.12, PyTorch 2.14.1 CPU, and Transformers 4.57.6. The exact model revisions are recorded in the provenance file. These results measure mention extraction only. They do not establish drug–ADR relationships or causality.
