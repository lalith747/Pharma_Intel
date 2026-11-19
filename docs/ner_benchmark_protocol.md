# NER benchmark protocol

## Freeze gold labels first

The benchmark CLI validates that every row has `review_status=complete`, an explicit JSON list in `gold_entities_json`, and exact character offsets. It refuses to download or run models while the annotation file is pending. Resolve `needs_adjudication` rows before changing their status to complete.

## Systems compared

1. `pharmaintel/case-study-lexical-baseline`: exact dictionary matching for clozapine, Clozaril, Leponex, and selected hematological outcome terms. This is a narrow target-pair baseline, not a general drug/ADR recognizer; interpret its overall recall accordingly.
2. `Glasgow-AI4BioMed/bioner_bc5cdr`: PubMed-domain token classifier with `Chemical` and `Disease` labels. The checkpoint card describes those labels and reports its own span-level results; neither label is identical to `DRUG` or `ADR`.
3. `d4data/biomedical-ner-all`: DistilBERT token classifier trained on MACCROBAT, with broad labels including `Medication`, `Disease_disorder`, and `Sign_symptom`.

For a common score table, the runner maps Chemical → DRUG; Disease → ADR; Medication → DRUG; and Disease_disorder, Sign_symptom, or Clinical_event → ADR. It retains each source label in prediction records. These mappings are operational benchmark choices, not claims of semantic equivalence. Check false positives carefully, particularly disease mentions that are indications rather than adverse events.

Model authors' test-set scores are not PharmaIntel metrics. Do not compare those published scores directly with our result table because training corpora, annotation policy, splits, and label definitions differ. Model confidence is not probability of causality.

## Metrics and reporting

- Exact entity type and exact character boundaries are required for a true positive; partial overlaps count as one false positive and one false negative.
- Report DRUG and ADR precision, recall, F1, support, and prediction count separately.
- Report `random_article` and `target_enriched` separately. The 80-row random article-balanced sample is the initial aggregate estimate; the 40-row enriched stratum is a challenge set and must not be pooled into that estimate.
- Include model ID, resolved model commit when available, tokenizer, aggregation strategy, and device from `ner_model_provenance.json`.
- Review false positives and false negatives before selecting a production checkpoint.

Run with:

```bash
python scripts/run_ner_benchmark.py
```

Predictions and metrics are written under the git-ignored `results/evaluation/` directory. Model weights are cached locally and are not committed.
