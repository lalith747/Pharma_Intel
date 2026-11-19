"""Build a corpus relevance audit and a reproducible manual NER sample."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from pharmaintel.evaluation.annotation import (
    build_corpus_relevance_review,
    sample_annotation_sentences,
    write_csv,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", default="data/raw/pubmed")
    parser.add_argument("--processed-dir", default="data/processed/pubmed")
    parser.add_argument("--annotated-dir", default="data/annotated")
    parser.add_argument("--random-articles", type=int, default=80)
    parser.add_argument("--enriched-articles", type=int, default=40)
    parser.add_argument("--seed", type=int, default=20261119)
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    processed_dir = Path(args.processed_dir)
    annotated_dir = Path(args.annotated_dir)
    metadata = json.loads((raw_dir / "retrieval_metadata.json").read_text(encoding="utf-8"))
    records = [
        json.loads(line)
        for line in (raw_dir / "pubmed_records.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    with (processed_dir / "pubmed_sentences.csv").open(encoding="utf-8-sig", newline="") as handle:
        sentence_rows = list(csv.DictReader(handle))

    relevance_rows = build_corpus_relevance_review(records, metadata["query"])
    abstracts_by_pmid = {str(record["pmid"]): record.get("abstract", "") for record in records}
    sample_rows = sample_annotation_sentences(
        sentence_rows,
        abstracts_by_pmid,
        random_article_count=args.random_articles,
        enriched_article_count=args.enriched_articles,
        seed=args.seed,
    )
    write_csv(processed_dir / "corpus_relevance_review.csv", relevance_rows)
    write_csv(annotated_dir / "ner_annotation_sample.csv", sample_rows)

    term_stats = Counter()
    for row in relevance_rows:
        for key in (
            "abstract_available",
            "drug_term_in_title",
            "adr_term_in_title",
            "drug_term_in_abstract",
            "adr_term_in_abstract",
        ):
            term_stats[key] += bool(row[key])
    summary = {
        "search_total": metadata["total_matching_records"],
        "records_fetched": len(records),
        "records_with_abstract": term_stats["abstract_available"],
        "records_without_abstract": len(records) - term_stats["abstract_available"],
        "records_with_drug_term_in_title": term_stats["drug_term_in_title"],
        "records_with_adr_term_in_title": term_stats["adr_term_in_title"],
        "records_with_drug_term_in_abstract": term_stats["drug_term_in_abstract"],
        "records_with_adr_term_in_abstract": term_stats["adr_term_in_abstract"],
        "manual_relevance_review_required": True,
        "sample_size": len(sample_rows),
        "sample_strata": dict(Counter(row["sampling_stratum"] for row in sample_rows)),
        "sampling_seed": args.seed,
        "sampling_note": "Random article-balanced stratum and target-enriched challenge stratum are kept separate.",
    }
    (processed_dir / "corpus_review_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
