"""Construct a provenance-preserving evidence graph from relation rows."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from typing import Any

import networkx as nx


def _safe_identifier(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.:-]+", "_", value.strip())
    return normalized or "unknown"


def build_evidence_graph(
    evidence_rows: Iterable[dict[str, Any]],
    ranked_signals: Iterable[dict[str, Any]] = (),
) -> nx.MultiDiGraph:
    """Build a directed multigraph linking drugs, events, evidence, and PMIDs.

    Every evidence node stores its exact sentence and relation/context cues.
    Relation edges describe extracted text only; they do not encode causality.
    """
    scores = {
        (str(row["drug"]).casefold(), str(row["adr"]).casefold()): float(row["priority_score"])
        for row in ranked_signals
    }
    graph = nx.MultiDiGraph(name="PharmaIntel PubMed evidence graph")
    evidence_number = 0
    for row in evidence_rows:
        drug = str(row.get("drug", "")).casefold().strip()
        adr = str(row.get("adr", "")).casefold().strip()
        pmid = str(row.get("pmid", "")).strip()
        sentence = str(row.get("evidence_sentence", ""))
        if not drug or not adr or not pmid or not sentence:
            continue
        drug_id = f"drug:{_safe_identifier(drug)}"
        adr_id = f"adr:{_safe_identifier(adr)}"
        pmid_id = f"publication:{_safe_identifier(pmid)}"
        evidence_number += 1
        evidence_id = (
            f"evidence:{_safe_identifier(pmid)}:{_safe_identifier(str(row.get('sentence_index', '0')))}:"
            f"{evidence_number:05d}"
        )
        graph.add_node(drug_id, node_type="drug", label=str(row.get("drug_surface", drug)))
        graph.add_node(adr_id, node_type="adverse_event", label=str(row.get("adr_surface", adr)))
        graph.add_node(
            pmid_id,
            node_type="publication",
            label=f"PMID {pmid}",
            pmid=pmid,
            title=str(row.get("title", "")),
            publication_date=str(row.get("publication_date", "")),
        )
        graph.add_node(
            evidence_id,
            node_type="evidence",
            label=f"{row.get('relation_status', 'unknown')} evidence",
            pmid=pmid,
            sentence_index=str(row.get("sentence_index", "")),
            sentence=sentence,
            relation_status=str(row.get("relation_status", "")),
            relation_cues_json=json.dumps(row.get("relation_cues", []), ensure_ascii=False),
            context_cues_json=json.dumps(row.get("context_cues", []), ensure_ascii=False),
            method=str(row.get("method", "")),
            priority_score=scores.get((drug, adr), 0.0),
        )
        graph.add_edge(evidence_id, drug_id, relation="mentions_drug")
        graph.add_edge(evidence_id, adr_id, relation="mentions_event")
        graph.add_edge(evidence_id, pmid_id, relation="published_in")
    return graph
