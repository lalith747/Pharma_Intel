"""Transparent ranking of deduplicated literature relation evidence."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

RELATION_STATUSES = {"supported", "speculative", "negated"}


def _paper_status(statuses: set[str]) -> str:
    positive = statuses & {"supported", "speculative"}
    negative = "negated" in statuses
    if positive and negative:
        return "mixed"
    if "supported" in positive:
        return "supported"
    if "speculative" in positive:
        return "speculative"
    return "negated"


def rank_safety_signals(evidence_rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank case-study pairs by unique-PMID support and assertion consistency.

    Per PMID, duplicate sentences contribute one paper-level status. For a
    mixed paper, the status is retained and contributes 0.5 to consistency.
    The score is `log(1 + positive PMIDs) * consistency`, where consistency is
    (supported + 0.5 * speculative + 0.5 * mixed) / all relation-assertion
    PMIDs. Co-mentions are excluded. This is a transparent triage score, not a
    probability, effect estimate, incidence, or causal strength.
    """
    by_pair_pmid: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    pair_surface: dict[tuple[str, str], tuple[str, str]] = {}
    pair_evidence_counts = defaultdict(int)
    for row in evidence_rows:
        status = str(row.get("relation_status", ""))
        if status not in {*RELATION_STATUSES, "co_mention"}:
            continue
        drug = str(row.get("drug", "")).casefold().strip()
        adr = str(row.get("adr", "")).casefold().strip()
        pmid = str(row.get("pmid", "")).strip()
        if not drug or not adr or not pmid:
            continue
        key = (drug, adr)
        pair_surface.setdefault(key, (str(row.get("drug_surface", row.get("drug", ""))),
                                      str(row.get("adr_surface", row.get("adr", "")))))
        pair_evidence_counts[key] += 1
        if status in RELATION_STATUSES:
            by_pair_pmid[key][pmid].add(status)

    ranked = []
    for key, paper_rows in by_pair_pmid.items():
        paper_statuses = [_paper_status(statuses) for statuses in paper_rows.values()]
        supported = paper_statuses.count("supported")
        speculative = paper_statuses.count("speculative")
        negated = paper_statuses.count("negated")
        mixed = paper_statuses.count("mixed")
        positive_pmids = supported + speculative + mixed
        assertion_pmids = len(paper_statuses)
        consistency = (
            (supported + 0.5 * speculative + 0.5 * mixed) / assertion_pmids
            if assertion_pmids else 0.0
        )
        score = math.log1p(positive_pmids) * consistency
        drug_surface, adr_surface = pair_surface[key]
        ranked.append(
            {
                "drug": key[0],
                "adr": key[1],
                "drug_surface_example": drug_surface,
                "adr_surface_example": adr_surface,
                "unique_pmid_count": len(paper_rows),
                "supported_pmid_count": supported,
                "speculative_pmid_count": speculative,
                "negated_pmid_count": negated,
                "mixed_pmid_count": mixed,
                "positive_pmid_count": positive_pmids,
                "consistency": consistency,
                "frequency_component": math.log1p(positive_pmids),
                "priority_score": score,
                "relation_evidence_occurrences": pair_evidence_counts[key],
                "score_method": "log1p(unique_positive_pmids)*assertion_consistency",
                "interpretation": "literature evidence triage only; not causal probability or incidence",
            }
        )
    return sorted(
        ranked,
        key=lambda row: (-row["priority_score"], -row["positive_pmid_count"], row["adr"]),
    )
