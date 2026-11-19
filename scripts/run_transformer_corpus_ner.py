"""Run pinned BC5CDR NER on the local PubMed sentence corpus."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import networkx as nx
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pharmaintel.knowledge_graph import build_evidence_graph
from pharmaintel.ner.huggingface import predict_entities
from pharmaintel.prioritization import rank_safety_signals
from pharmaintel.relation_extraction import extract_sentence_relations

MODEL = "Glasgow-AI4BioMed/bioner_bc5cdr"
REVISION = "6eaba08f3ae3f12ba15b3ff02d41aa31705bf30f"
SENTENCES = ROOT / "data/processed/pubmed/pubmed_sentences.csv"
OUT_DIR = ROOT / "data/processed/pubmed"
RESULTS = ROOT / "results"
TARGET_ADRS = {"neutropenia", "neutropenic", "agranulocytosis", "granulocytopenia", "leukopenia", "leucopenia"}


def _clozapine(value: str) -> bool:
    return value.casefold().strip() in {"clozapine", "clozaril", "leponex"}


def _source_entity(entities: list[dict[str, Any]], mention: dict[str, Any]) -> dict[str, Any]:
    """Recover the original NER label and score for a relation mention span."""
    return next(
        (
            entity for entity in entities
            if entity.get("start") == mention.get("start")
            and entity.get("end") == mention.get("end")
        ),
        {},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-files-only", action="store_true", help="Fail unless the pinned model is already cached.")
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()
    if not SENTENCES.exists():
        raise FileNotFoundError(SENTENCES)
    frame = pd.read_csv(SENTENCES, dtype={"pmid": str}, keep_default_na=False)
    required = {"pmid", "sentence_index", "sentence"}
    if missing := required - set(frame.columns):
        raise ValueError(f"Sentence corpus missing columns: {sorted(missing)}")
    texts = frame["sentence"].astype(str).tolist()
    started = time.monotonic()

    def progress(done: int, total: int) -> None:
        print(f"NER inference: {done:,}/{total:,} sentences", flush=True)

    predictions, provenance = predict_entities(
        texts, MODEL, batch_size=args.batch_size, device=-1, revision=REVISION,
        local_files_only=args.local_files_only, progress_callback=progress,
    )
    if len(predictions) != len(frame):
        raise RuntimeError("NER output count does not match corpus row count.")

    sentence_rows: list[dict[str, Any]] = []
    relation_rows: list[dict[str, Any]] = []
    label_counts: Counter[str] = Counter()
    for source, entities in zip(frame.to_dict(orient="records"), predictions, strict=True):
        text = str(source["sentence"])
        for entity in entities:
            label_counts[str(entity.get("source_label", "unknown"))] += 1
        sentence_rows.append({
            "pmid": str(source["pmid"]),
            "sentence_index": str(source["sentence_index"]),
            "sentence": text,
            "entities": entities,
        })
        relations = extract_sentence_relations(text, entities, use_case_study_lexicon=False)
        for relation in relations:
            drug_surface = relation["drug"]["text"]
            adr_surface = relation["adr"]["text"]
            drug_prediction = _source_entity(entities, relation["drug"])
            adr_prediction = _source_entity(entities, relation["adr"])
            relation_rows.append({
                "pmid": str(source["pmid"]),
                "record_type": str(source.get("record_type", "")),
                "title": str(source.get("title", "")),
                "journal": str(source.get("journal", "")),
                "publication_date": str(source.get("publication_date", "")),
                "sentence_index": str(source["sentence_index"]),
                "drug": drug_surface.casefold().strip(),
                "drug_surface": drug_surface,
                "adr": adr_surface.casefold().strip(),
                "adr_surface": adr_surface,
                "drug_model_label": drug_prediction.get("source_label", ""),
                "adr_model_label": adr_prediction.get("source_label", ""),
                "drug_model_score": drug_prediction.get("score"),
                "adr_model_score": adr_prediction.get("score"),
                "evidence_sentence": text,
                "relation_status": (
                    "co_mention" if relation["evidence_class"] == "co_mention_only"
                    else "negated" if relation["assertion"] == "negated"
                    else "speculative" if relation["assertion"] == "speculative"
                    else "supported"
                ),
                "evidence_class": relation["evidence_class"],
                "relation_cues": relation["relation_cues"],
                "context_cues": relation["context_cues"],
                "method": "BC5CDR_NER_plus_pair_scoped_lexical_relation_baseline",
            })

    # The checkpoint's Disease class is not ADR-specific. For case study ranking,
    # retain the predeclared blood-event vocabulary and clozapine aliases only.
    case_rows = [row for row in relation_rows
                 if _clozapine(row["drug_surface"]) and row["adr"].casefold() in TARGET_ADRS]
    case_evidence = [{**row, "drug": "clozapine"} for row in case_rows]
    ranked = rank_safety_signals(case_evidence)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "bc5cdr_ner_predictions.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in sentence_rows), encoding="utf-8"
    )
    pd.DataFrame(relation_rows).to_csv(OUT_DIR / "transformer_relation_evidence.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(case_evidence).to_csv(OUT_DIR / "transformer_case_study_evidence.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(ranked).to_csv(RESULTS / "transformer_case_study_signals.csv", index=False, encoding="utf-8-sig")
    graph = build_evidence_graph(case_evidence, ranked)
    graph_path = RESULTS / "pharmaintel_transformer_case_graph.graphml"
    nx.write_graphml(graph, graph_path)
    round_trip = nx.read_graphml(graph_path)
    evidence_nodes = [(node, data) for node, data in round_trip.nodes(data=True) if data.get("node_type") == "evidence"]
    if len(evidence_nodes) != len(case_evidence):
        raise RuntimeError("Transformer evidence graph round-trip failed provenance count check.")

    summary = {
        "model": provenance,
        "model_label_mapping": {"Chemical": "DRUG candidate", "Disease": "ADR candidate"},
        "mapping_limit": "BC5CDR Chemical and Disease classes are broad; not every Chemical is a drug and not every Disease is an ADR.",
        "device": "cpu",
        "local_files_only": args.local_files_only,
        "runtime_seconds": round(time.monotonic() - started, 2),
        "sentences_scanned": len(frame),
        "unique_pmids_scanned": int(frame["pmid"].nunique()),
        "entity_counts_by_raw_label": dict(sorted(label_counts.items())),
        "all_model_pair_rows": len(relation_rows),
        "case_study_pair_rows": len(case_evidence),
        "case_study_signal_count": len(ranked),
        "case_study_relation_status_counts": dict(sorted(Counter(row["relation_status"] for row in case_evidence).items())),
        "graph_nodes": round_trip.number_of_nodes(),
        "graph_edges": round_trip.number_of_edges(),
        "evaluation": "No corpus-level precision/recall/F1 reported because this corpus has no independent sentence-level NER or relation gold labels.",
        "score_interpretation": "Literature evidence triage only; not a causal probability, effect estimate, incidence, or validated clinical signal.",
    }
    (RESULTS / "transformer_corpus_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
