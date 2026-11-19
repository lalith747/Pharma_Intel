"""Extract case-study relation evidence and produce ranked signals + graph."""

from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import networkx as nx
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pharmaintel.knowledge_graph import build_evidence_graph
from pharmaintel.ner.rule_baseline import extract_case_study_entities
from pharmaintel.prioritization import rank_safety_signals
from pharmaintel.relation_extraction import extract_sentence_relations

SENTENCES = PROJECT_ROOT / "data/processed/pubmed/pubmed_sentences.csv"
EVIDENCE = PROJECT_ROOT / "data/processed/pubmed/relation_evidence.csv"
RANKED = PROJECT_ROOT / "results/ranked_signals.csv"
SUMMARY = PROJECT_ROOT / "results/evaluation/corpus_relation_summary.json"
GRAPH = PROJECT_ROOT / "results/pharmaintel_evidence_graph.graphml"


def _canonical_drug(value: str) -> str:
    normalized = value.casefold().strip()
    return "clozapine" if normalized in {"clozapine", "clozaril", "leponex"} else normalized


def _relation_status(record: dict[str, Any]) -> str:
    if record["evidence_class"] == "co_mention_only":
        return "co_mention"
    if record["assertion"] == "negated":
        return "negated"
    if record["assertion"] == "speculative":
        return "speculative"
    return "supported"


def validate_generated_outputs(
    evidence: list[dict[str, Any]], ranked: list[dict[str, Any]], graph_path: Path
) -> dict[str, Any]:
    """Check score integrity and GraphML round-trip provenance before reporting."""
    pair_keys = [(row["drug"], row["adr"]) for row in ranked]
    if len(pair_keys) != len(set(pair_keys)):
        raise ValueError("Ranked CSV contains duplicate normalized drug–ADR pairs.")
    if any(not math.isfinite(float(row["priority_score"])) for row in ranked):
        raise ValueError("Ranked signal contains a non-finite score.")
    if any(not 0.0 <= float(row["consistency"]) <= 1.0 for row in ranked):
        raise ValueError("Assertion consistency must be between 0 and 1.")
    if ranked != sorted(
        ranked, key=lambda row: (-row["priority_score"], -row["positive_pmid_count"], row["adr"])
    ):
        raise ValueError("Ranked signal rows are not ordered by the documented rank keys.")

    loaded = nx.read_graphml(graph_path)
    evidence_nodes = [
        (node, data) for node, data in loaded.nodes(data=True) if data.get("node_type") == "evidence"
    ]
    if len(evidence_nodes) != len(evidence):
        raise ValueError("GraphML round-trip changed the evidence-node count.")
    for node, data in evidence_nodes:
        outgoing = list(loaded.out_edges(node, data=True))
        relations = {edge[2].get("relation") for edge in outgoing}
        if len(outgoing) != 3 or relations != {"mentions_drug", "mentions_event", "published_in"}:
            raise ValueError(f"Evidence node {node} is missing a provenance edge.")
        if not data.get("pmid") or not data.get("sentence"):
            raise ValueError(f"Evidence node {node} lost source provenance during GraphML round-trip.")
    if len(evidence) and not evidence_nodes:
        raise ValueError("The generated graph has no evidence nodes.")
    return {
        "ranked_pairs_unique": len(pair_keys),
        "ranked_scores_finite": True,
        "consistency_in_range": True,
        "graphml_round_trip": True,
        "evidence_nodes_with_three_provenance_edges": len(evidence_nodes),
    }


def extract_corpus_evidence(frame: pd.DataFrame) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    seen_sentence_pairs: set[tuple[str, str, str]] = set()
    for source in frame.to_dict(orient="records"):
        sentence = str(source.get("sentence", ""))
        entities = extract_case_study_entities(sentence)
        if not entities:
            continue
        relations = extract_sentence_relations(sentence, entities)
        for relation in relations:
            drug_surface = str(relation["drug"]["text"])
            adr_surface = str(relation["adr"]["text"])
            drug = _canonical_drug(drug_surface)
            adr = adr_surface.casefold().strip()
            pmid = str(source.get("pmid", "")).strip()
            sentence_index = str(source.get("sentence_index", ""))
            key = (pmid, sentence_index, f"{drug}|{adr}")
            if key in seen_sentence_pairs:
                continue
            seen_sentence_pairs.add(key)
            evidence.append(
                {
                    "pmid": pmid,
                    "record_type": str(source.get("record_type", "")),
                    "title": str(source.get("title", "")),
                    "journal": str(source.get("journal", "")),
                    "publication_date": str(source.get("publication_date", "")),
                    "sentence_index": sentence_index,
                    "drug": drug,
                    "drug_surface": drug_surface,
                    "adr": adr,
                    "adr_surface": adr_surface,
                    "evidence_sentence": sentence,
                    "relation_status": _relation_status(relation),
                    "evidence_class": relation["evidence_class"],
                    "relation_cues": relation["relation_cues"],
                    "context_cues": relation["context_cues"],
                    "causal_language": relation["causal_language"],
                    "causal_conclusion": None,
                    "method": "case_study_lexicon_pair_scoped_rule_baseline",
                }
            )
    return evidence


def main() -> None:
    if not SENTENCES.exists():
        raise FileNotFoundError(f"Missing PubMed sentence file: {SENTENCES}")
    frame = pd.read_csv(SENTENCES, dtype={"pmid": str}, keep_default_na=False)
    if not {"pmid", "sentence_index", "sentence"}.issubset(frame.columns):
        raise ValueError("PubMed sentence CSV must include pmid, sentence_index, and sentence.")

    evidence = extract_corpus_evidence(frame)
    ranked = rank_safety_signals(evidence)
    evidence_frame = pd.DataFrame(evidence)
    ranked_frame = pd.DataFrame(ranked)
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    RANKED.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    GRAPH.parent.mkdir(parents=True, exist_ok=True)
    evidence_frame.to_csv(EVIDENCE, index=False, encoding="utf-8-sig")
    ranked_frame.to_csv(RANKED, index=False, encoding="utf-8-sig")

    graph = build_evidence_graph(evidence, ranked)
    nx.write_graphml(graph, GRAPH)
    verification = validate_generated_outputs(evidence, ranked, GRAPH)
    status_counts = Counter(row["relation_status"] for row in evidence)
    summary = {
        "source": "local PubMed sentence corpus retrieved by the project",
        "source_file": "data/processed/pubmed/pubmed_sentences.csv",
        "sentences_scanned": len(frame),
        "unique_pmids_scanned": int(frame["pmid"].nunique()),
        "sentence_pair_evidence_rows": len(evidence),
        "unique_signal_pairs": len(ranked),
        "graph_node_count": graph.number_of_nodes(),
        "graph_edge_count": graph.number_of_edges(),
        "verification": verification,
        "relation_status_counts": dict(sorted(status_counts.items())),
        "case_study_scope": "case-study lexicon only; clozapine aliases canonicalized; ADR surface terms preserved",
        "relation_method": "pair-scoped lexical relation cues and assertion cues",
        "score_formula": "log1p(unique positive PMIDs) * assertion consistency; supported=1, speculative=0.5, negated=0; mixed PMID=0.5 consistency credit",
        "score_limitation": "triage score only; not a causal probability, effect estimate, incidence, or validated clinical signal",
        "annotation_limitation": "relation baseline has only an assistant-curated development pilot, not independent human-gold validation",
        "outputs": {
            "evidence": "data/processed/pubmed/relation_evidence.csv",
            "ranked_signals": "results/ranked_signals.csv",
            "knowledge_graph": "results/pharmaintel_evidence_graph.graphml",
        },
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Ranked signals: {RANKED}")
    print(f"Evidence graph: {GRAPH}")


if __name__ == "__main__":
    main()
