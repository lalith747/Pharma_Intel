import math

from pharmaintel.knowledge_graph import build_evidence_graph
from pharmaintel.prioritization import rank_safety_signals


def test_ranking_deduplicates_papers_and_discounts_speculation_and_negation():
    evidence = [
        {"drug": "clozapine", "adr": "neutropenia", "pmid": "1", "relation_status": "supported"},
        {"drug": "clozapine", "adr": "neutropenia", "pmid": "1", "relation_status": "supported"},
        {"drug": "clozapine", "adr": "neutropenia", "pmid": "2", "relation_status": "speculative"},
        {"drug": "clozapine", "adr": "neutropenia", "pmid": "3", "relation_status": "negated"},
        {
            "drug": "clozapine",
            "adr": "agranulocytosis",
            "pmid": "4",
            "relation_status": "co_mention",
        },
    ]

    ranked = rank_safety_signals(evidence)
    neutropenia = next(row for row in ranked if row["adr"] == "neutropenia")

    assert neutropenia["unique_pmid_count"] == 3
    assert neutropenia["positive_pmid_count"] == 2
    assert neutropenia["supported_pmid_count"] == 1
    assert neutropenia["speculative_pmid_count"] == 1
    assert neutropenia["negated_pmid_count"] == 1
    assert neutropenia["consistency"] == 0.5
    assert neutropenia["priority_score"] == math.log1p(2) * 0.5
    assert all(row["adr"] != "agranulocytosis" for row in ranked)


def test_mixed_paper_is_explicit_and_score_is_not_a_probability():
    ranked = rank_safety_signals(
        [
            {
                "drug": "clozapine",
                "adr": "neutropenia",
                "pmid": "1",
                "relation_status": "supported",
            },
            {"drug": "clozapine", "adr": "neutropenia", "pmid": "1", "relation_status": "negated"},
        ]
    )[0]

    assert ranked["mixed_pmid_count"] == 1
    assert ranked["consistency"] == 0.5
    assert "not causal probability" in ranked["interpretation"]


def test_evidence_graph_preserves_source_sentence_and_pmid_edges():
    row = {
        "drug": "clozapine",
        "drug_surface": "Clozapine",
        "adr": "neutropenia",
        "adr_surface": "neutropenia",
        "pmid": "12345",
        "title": "A case report",
        "publication_date": "2024",
        "sentence_index": "2",
        "evidence_sentence": "Clozapine may cause neutropenia.",
        "relation_status": "speculative",
        "relation_cues": [{"text": "cause", "start": 13, "end": 18}],
        "context_cues": [{"text": "may", "start": 9, "end": 12}],
        "method": "test baseline",
    }
    graph = build_evidence_graph([row], [])

    evidence_nodes = [
        node for node, data in graph.nodes(data=True) if data["node_type"] == "evidence"
    ]
    assert len(evidence_nodes) == 1
    evidence_node = evidence_nodes[0]
    assert graph.nodes[evidence_node]["sentence"] == row["evidence_sentence"]
    assert graph.nodes[evidence_node]["pmid"] == "12345"
    assert {data["relation"] for _, _, data in graph.out_edges(evidence_node, data=True)} == {
        "mentions_drug",
        "mentions_event",
        "published_in",
    }
