"""Prepare reproducible corpus-review and manual NER annotation templates."""

from __future__ import annotations

import csv
import random
import re
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

DRUG_ALIASES = ("clozapine", "clozaril", "leponex")
ADR_ALIASES = (
    "neutropenia",
    "neutropenic",
    "agranulocytosis",
    "granulocytopenia",
    "granulocytopenic",
    "leukopenia",
    "leucopenia",
)


def _contains_term(text: str, terms: Iterable[str]) -> bool:
    return any(re.search(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE) for term in terms)


def build_corpus_relevance_review(
    records: list[dict[str, Any]],
    query: str,
    drug_terms: Iterable[str] = DRUG_ALIASES,
    adr_terms: Iterable[str] = ADR_ALIASES,
) -> list[dict[str, Any]]:
    """Create a blinded manual relevance-review sheet with lexical audit flags."""
    drug_terms, adr_terms = tuple(drug_terms), tuple(adr_terms)
    rows = []
    for position, record in enumerate(records, start=1):
        title = str(record.get("title", ""))
        abstract = str(record.get("abstract", ""))
        rows.append(
            {
                "search_position": position,
                "pmid": str(record.get("pmid", "")),
                "title": title,
                "publication_date": record.get("publication_date", ""),
                "abstract_available": bool(abstract.strip()),
                "drug_term_in_title": _contains_term(title, drug_terms),
                "adr_term_in_title": _contains_term(title, adr_terms),
                "drug_term_in_abstract": _contains_term(abstract, drug_terms),
                "adr_term_in_abstract": _contains_term(abstract, adr_terms),
                "query": query,
                "manual_relevance": "",
                "review_notes": "",
            }
        )
    return rows


def sample_annotation_sentences(
    sentence_rows: list[dict[str, Any]],
    abstracts_by_pmid: dict[str, str],
    random_article_count: int = 80,
    enriched_article_count: int = 40,
    seed: int = 20261119,
    drug_terms: Iterable[str] = DRUG_ALIASES,
    adr_terms: Iterable[str] = ADR_ALIASES,
) -> list[dict[str, Any]]:
    """Sample one sentence per paper, separating random and target-enriched strata.

    The random stratum samples papers uniformly and is the only stratum intended for
    a first-pass aggregate estimate. The enriched stratum is a separate challenge set.
    """
    if random_article_count < 0 or enriched_article_count < 0:
        raise ValueError("Sample sizes must be non-negative.")
    drug_terms, adr_terms = tuple(drug_terms), tuple(adr_terms)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sentence_rows:
        pmid = str(row.get("pmid", "")).strip()
        if pmid and str(row.get("sentence", "")).strip():
            groups[pmid].append(row)

    rng = random.Random(seed)
    available_pmids = sorted(groups)
    random_pmids = set(rng.sample(available_pmids, min(random_article_count, len(available_pmids))))
    selected: list[tuple[str, str, dict[str, Any]]] = []
    for pmid in sorted(random_pmids):
        selected.append(("random_article", pmid, rng.choice(groups[pmid])))

    enriched_candidates: dict[str, list[dict[str, Any]]] = {}
    for pmid in available_pmids:
        if pmid in random_pmids:
            continue
        matching = [
            row
            for row in groups[pmid]
            if _contains_term(str(row["sentence"]), drug_terms)
            and _contains_term(str(row["sentence"]), adr_terms)
        ]
        if matching:
            enriched_candidates[pmid] = matching
    enriched_pmids = rng.sample(
        sorted(enriched_candidates), min(enriched_article_count, len(enriched_candidates))
    )
    for pmid in sorted(enriched_pmids):
        selected.append(("target_enriched", pmid, rng.choice(enriched_candidates[pmid])))

    # Restore stable IDs after seeded sampling.
    selected.sort(key=lambda item: (item[0], item[1], int(item[2].get("sentence_index", 0))))
    output = []
    for index, (stratum, pmid, sentence_row) in enumerate(selected, start=1):
        output.append(
            {
                "sample_id": f"NER{index:04d}",
                "sampling_stratum": stratum,
                "pmid": pmid,
                "record_type": sentence_row.get("record_type", "pubmed_article"),
                "sentence_index": sentence_row.get("sentence_index", ""),
                "sentence": sentence_row.get("sentence", ""),
                "title": sentence_row.get("title", ""),
                "abstract_context": abstracts_by_pmid.get(pmid, ""),
                "query": sentence_row.get("query", ""),
                "retrieved_at_utc": sentence_row.get("retrieved_at_utc", ""),
                "gold_entities_json": "",
                "annotator_notes": "",
                "review_status": "pending",
            }
        )
    return output


def write_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    """Write a UTF-8 CSV with stable columns, including when it has no rows."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        target.write_text("", encoding="utf-8")
        return
    with target.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def find_exact_occurrences(sentence: str, mention: str) -> list[tuple[int, int]]:
    """Find case-insensitive mention occurrences and return zero-based half-open offsets."""
    mention = mention.strip()
    if not mention:
        return []
    return [
        (match.start(), match.end())
        for match in re.finditer(re.escape(mention), sentence, flags=re.IGNORECASE)
    ]


def make_annotation_entity(
    sentence: str, mention: str, label: str, occurrence_index: int = 0
) -> dict[str, Any]:
    """Create an entity span from exact text; preserve the source sentence's casing."""
    if label not in {"DRUG", "ADR"}:
        raise ValueError("label must be DRUG or ADR.")
    occurrences = find_exact_occurrences(sentence, mention)
    if not occurrences:
        raise ValueError("Mention text was not found in the sentence.")
    if not 0 <= occurrence_index < len(occurrences):
        raise IndexError("occurrence_index is outside the matching occurrences.")
    start, end = occurrences[occurrence_index]
    return {"text": sentence[start:end], "label": label, "start": start, "end": end}
