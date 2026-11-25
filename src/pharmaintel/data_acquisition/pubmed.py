"""Reproducible PubMed retrieval using NCBI E-utilities via Biopython."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from Bio import Entrez

DEFAULT_QUERY = '"clozapine"[Title/Abstract] AND "neutropenia"[Title/Abstract]'
DEFAULT_BATCH_SIZE = 100
MAX_PUBMED_RESULTS = 10_000


class PubMedError(RuntimeError):
    """Raised when a PubMed search or record retrieval cannot be completed."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def configure_entrez(email: str | None = None, api_key: str | None = None) -> None:
    """Configure Biopython's shared Entrez client from arguments or environment."""
    Entrez.email = email or os.getenv("NCBI_EMAIL") or None
    Entrez.api_key = api_key or os.getenv("NCBI_API_KEY") or None
    Entrez.tool = "PharmaIntelAI"


def search_pubmed(query: str, max_results: int, sort: str = "relevance") -> dict[str, Any]:
    """Search PubMed and return IDs plus the search translation and total count."""
    if not query.strip():
        raise ValueError("PubMed query cannot be empty.")
    if not 1 <= max_results <= MAX_PUBMED_RESULTS:
        raise ValueError(f"max_results must be between 1 and {MAX_PUBMED_RESULTS}.")

    try:
        with Entrez.esearch(
            db="pubmed", term=query, retmax=max_results, sort=sort, usehistory="n"
        ) as handle:
            result = Entrez.read(handle)
    except Exception as exc:  # Biopython raises several HTTP/XML exception types.
        raise PubMedError(f"PubMed search failed: {exc}") from exc

    return {
        "query_translation": str(result.get("QueryTranslation", "")),
        "total_matching_records": int(result.get("Count", 0)),
        "pmids": [str(pmid) for pmid in result.get("IdList", [])],
    }


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _publication_date(article: dict[str, Any]) -> str:
    journal = article.get("Journal", {})
    pub_date = journal.get("JournalIssue", {}).get("PubDate", {})
    if isinstance(pub_date, dict):
        date_parts = [
            _text(pub_date.get(key))
            for key in ("Year", "Month", "Day", "MedlineDate")
            if pub_date.get(key)
        ]
        if date_parts:
            return " ".join(date_parts)
    article_dates = article.get("ArticleDate", [])
    if article_dates:
        first = article_dates[0]
        return "-".join(_text(first.get(key)) for key in ("Year", "Month", "Day") if first.get(key))
    return ""


def _abstract_text(article: dict[str, Any]) -> str:
    abstract = article.get("Abstract", {}).get("AbstractText", [])
    sections: list[str] = []
    for section in abstract:
        content = _text(section)
        label = _text(getattr(section, "attributes", {}).get("Label", ""))
        if content:
            sections.append(f"{label}: {content}" if label else content)
    return "\n".join(sections)


def _authors(article: dict[str, Any]) -> list[str]:
    raw_authors = article.get("AuthorList", [])
    # PubMed Bookshelf records wrap authors in a typed list inside Book.AuthorList.
    if raw_authors and isinstance(raw_authors[0], list):
        raw_authors = raw_authors[0]
    names: list[str] = []
    for author in raw_authors:
        if author.get("CollectiveName"):
            names.append(_text(author["CollectiveName"]))
        else:
            name = " ".join(
                _text(author.get(key)) for key in ("ForeName", "LastName") if author.get(key)
            )
            if name:
                names.append(name)
    return names


def normalize_pubmed_article(item: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a journal article or Bookshelf record to stable JSON-compatible fields."""
    if "BookDocument" in item:
        document = item["BookDocument"]
        book = document.get("Book", {})
        pmid = _text(document.get("PMID"))
        if not pmid:
            return None
        doi = ""
        for article_id in document.get("ArticleIdList", []):
            if getattr(article_id, "attributes", {}).get("IdType") == "doi":
                doi = _text(article_id)
                break
        pub_date = book.get("PubDate", {})
        date = " ".join(
            _text(pub_date.get(key)) for key in ("Year", "Month", "Day") if pub_date.get(key)
        )
        return {
            "pmid": pmid,
            "record_type": "pubmed_book",
            "title": _text(book.get("BookTitle")),
            "abstract": _abstract_text(document),
            "journal": _text(book.get("CollectionTitle")),
            "publication_date": date,
            "doi": doi,
            "authors": _authors(book),
        }

    citation = item.get("MedlineCitation", {})
    article = citation.get("Article", {})
    pmid = _text(citation.get("PMID"))
    if not pmid:
        return None

    doi = ""
    for article_id in item.get("PubmedData", {}).get("ArticleIdList", []):
        if getattr(article_id, "attributes", {}).get("IdType") == "doi":
            doi = _text(article_id)
            break

    return {
        "pmid": pmid,
        "record_type": "pubmed_article",
        "title": _text(article.get("ArticleTitle")),
        "abstract": _abstract_text(article),
        "journal": _text(article.get("Journal", {}).get("Title")),
        "publication_date": _publication_date(article),
        "doi": doi,
        "authors": _authors(article),
    }


def fetch_pubmed_records(
    pmids: Iterable[str], batch_size: int = DEFAULT_BATCH_SIZE
) -> list[dict[str, Any]]:
    """Fetch and normalize PMIDs in batches to keep requests bounded."""
    ids = [str(pmid) for pmid in pmids]
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1.")
    records: list[dict[str, Any]] = []
    for start in range(0, len(ids), batch_size):
        batch = ids[start : start + batch_size]
        try:
            with Entrez.efetch(db="pubmed", id=",".join(batch), retmode="xml") as handle:
                response = Entrez.read(handle)
        except Exception as exc:
            raise PubMedError(
                f"PubMed fetch failed for batch starting at PMID {batch[0]}: {exc}"
            ) from exc
        for item in [*response.get("PubmedArticle", []), *response.get("PubmedBookArticle", [])]:
            record = normalize_pubmed_article(item)
            if record:
                records.append(record)
    return records


def deduplicate_records(records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Keep the first record for each non-empty PMID and report removed duplicates."""
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    duplicate_count = 0
    for record in records:
        pmid = str(record.get("pmid", "")).strip()
        if not pmid:
            continue
        if pmid in seen:
            duplicate_count += 1
            continue
        seen.add(pmid)
        unique.append({**record, "pmid": pmid})
    return unique, duplicate_count


_ABBREVIATIONS = (
    "e.g.",
    "i.e.",
    "et al.",
    "vs.",
    "resp.",
    "Fig.",
    "Figs.",
    "Eq.",
    "No.",
    "Dr.",
    "Prof.",
    "St.",
    "U.S.",
    "U.K.",
    "a.m.",
    "p.m.",
)
_ABBREVIATION_PATTERN = re.compile(
    r"(?<!\w)(?:" + "|".join(re.escape(item) for item in _ABBREVIATIONS) + r")",
    flags=re.IGNORECASE,
)
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[\"'“‘(\[]?[A-Z0-9])")


def clean_text(text: str) -> str:
    """Normalize whitespace while retaining punctuation and abstract section labels."""
    return " ".join(str(text or "").replace("\u00a0", " ").split())


def split_sentences(text: str) -> list[str]:
    """Split an abstract with a deterministic rule splitter and common abbreviation guards."""
    normalized = clean_text(text)
    if not normalized:
        return []
    marker = "\ue000"
    protected = _ABBREVIATION_PATTERN.sub(
        lambda match: match.group().replace(".", marker), normalized
    )
    sentences = [part.strip().replace(marker, ".") for part in _SENTENCE_BOUNDARY.split(protected)]
    return [sentence for sentence in sentences if sentence]


def build_sentence_rows(
    records: Iterable[dict[str, Any]], query: str, retrieved_at: str
) -> list[dict[str, Any]]:
    """Create sentence rows that retain article identifiers and search provenance."""
    rows: list[dict[str, Any]] = []
    for record in records:
        for index, sentence in enumerate(split_sentences(record.get("abstract", "")), start=1):
            rows.append(
                {
                    "pmid": record["pmid"],
                    "record_type": record.get("record_type", "pubmed_article"),
                    "sentence_index": index,
                    "sentence": sentence,
                    "title": record.get("title", ""),
                    "journal": record.get("journal", ""),
                    "publication_date": record.get("publication_date", ""),
                    "query": query,
                    "retrieved_at_utc": retrieved_at,
                }
            )
    return rows


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_pipeline(
    query: str = DEFAULT_QUERY,
    max_results: int = 100,
    batch_size: int = DEFAULT_BATCH_SIZE,
    raw_dir: str | Path = "data/raw/pubmed",
    processed_dir: str | Path = "data/processed/pubmed",
    email: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Search, fetch, deduplicate, sentence-split, and save a provenance-preserving dataset."""
    configure_entrez(email=email, api_key=api_key)
    raw_path, processed_path = Path(raw_dir), Path(processed_dir)
    raw_path.mkdir(parents=True, exist_ok=True)
    processed_path.mkdir(parents=True, exist_ok=True)

    search = search_pubmed(query=query, max_results=max_results)
    retrieved_at = _utc_now()
    fetched = fetch_pubmed_records(search["pmids"], batch_size=batch_size)
    records, duplicate_count = deduplicate_records(fetched)
    sentence_rows = build_sentence_rows(records, query=query, retrieved_at=retrieved_at)
    fetched_pmids = {record["pmid"] for record in records}
    pmids_not_fetched = [pmid for pmid in search["pmids"] if pmid not in fetched_pmids]

    metadata = {
        "source": "PubMed via NCBI E-utilities",
        "query": query,
        "query_translation": search["query_translation"],
        "sort": "relevance",
        "searched_at_utc": retrieved_at,
        "total_matching_records": search["total_matching_records"],
        "requested_max_results": max_results,
        "pmids_returned_by_search": len(search["pmids"]),
        "records_fetched": len(fetched),
        "unique_records_saved": len(records),
        "duplicate_records_removed": duplicate_count,
        "pmids_not_fetched": pmids_not_fetched,
        "pmids_not_fetched_count": len(pmids_not_fetched),
        "records_with_abstract": sum(bool(record["abstract"]) for record in records),
        "sentence_count": len(sentence_rows),
        "biopython_version": __import__("Bio").__version__,
    }

    _write_jsonl(raw_path / "pubmed_records.jsonl", records)
    (raw_path / "retrieval_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    pd.DataFrame(records).to_csv(processed_path / "pubmed_records.csv", index=False)
    sentence_columns = [
        "pmid",
        "record_type",
        "sentence_index",
        "sentence",
        "title",
        "journal",
        "publication_date",
        "query",
        "retrieved_at_utc",
    ]
    pd.DataFrame(sentence_rows, columns=sentence_columns).to_csv(
        processed_path / "pubmed_sentences.csv", index=False
    )
    return metadata


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--query", default=DEFAULT_QUERY, help="PubMed query (default: case study)."
    )
    parser.add_argument(
        "--max-results", type=int, default=100, help="Maximum PMIDs to retrieve (1–10000)."
    )
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--raw-dir", default="data/raw/pubmed")
    parser.add_argument("--processed-dir", default="data/processed/pubmed")
    parser.add_argument(
        "--email", default=None, help="Contact email; may also be set with NCBI_EMAIL."
    )
    parser.add_argument(
        "--api-key", default=None, help="NCBI API key; may also be set with NCBI_API_KEY."
    )
    args = parser.parse_args(argv)
    if not (args.email or os.getenv("NCBI_EMAIL")):
        print("Note: set NCBI_EMAIL to identify this client to NCBI.", file=sys.stderr)
    try:
        metadata = run_pipeline(
            query=args.query,
            max_results=args.max_results,
            batch_size=args.batch_size,
            raw_dir=args.raw_dir,
            processed_dir=args.processed_dir,
            email=args.email,
            api_key=args.api_key,
        )
    except (PubMedError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
