"""Build a pair-level relation pilot from the reviewed NER sentence sample."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pharmaintel.relation_extraction import extract_sentence_relations  # noqa: E402

INPUT = PROJECT_ROOT / "data/annotated/ner_annotation_sample.csv"
OUTPUT = PROJECT_ROOT / "data/annotated/relation_annotation_sample.csv"

# First-pass labels assigned from sentence context. These are provisional
# assistant-curated labels, not independent human gold annotations.
GOLD: dict[tuple[str, str, str], str] = {
    ("NER0002", "clozapine", "neutropenia"): "supported",
    ("NER0002", "olanzapine", "neutropenia"): "co_mention",
    ("NER0007", "clozapine", "neutropenia"): "supported",
    ("NER0012", "olanzapine", "leucopenia"): "supported",
    ("NER0012", "olanzapine", "neutropenia"): "supported",
    ("NER0014", "clozapine", "blood dyscrasia"): "supported",
    ("NER0014", "lithium", "blood dyscrasia"): "co_mention",
    ("NER0016", "clozapine", "neutropenia"): "supported",
    ("NER0016", "clozapine", "agranulocytosis"): "supported",
    ("NER0019", "clozapine", "neutropenia"): "supported",
    ("NER0021", "clozapine", "neutropenia"): "unclear",
    ("NER0021", "olanzapine", "neutropenia"): "unclear",
    ("NER0022", "lithium carbonate", "neutropenia"): "co_mention",
    ("NER0022", "clozapine", "neutropenia"): "supported",
    ("NER0025", "clozapine", "absolute neutropenia"): "supported",
    ("NER0025", "clozapine", "agranulocytosis"): "supported",
    ("NER0026", "clozapine", "fever"): "supported",
    ("NER0028", "clozapine", "neutropenia"): "supported",
    ("NER0028", "clozapine", "leukopenia"): "supported",
    ("NER0028", "lithium", "neutropenia"): "co_mention",
    ("NER0028", "lithium", "leukopenia"): "co_mention",
    ("NER0030", "clozapine", "febrile neutropenia"): "supported",
    ("NER0030", "clozapine", "cellulitis"): "supported",
    ("NER0031", "clozapine", "neutropenia"): "unclear",
    ("NER0036", "olanzapine", "neutropenia"): "supported",
    ("NER0036", "clozapine", "neutropenia"): "supported",
    ("NER0041", "clozapine", "sepsis-like presentation"): "unclear",
    ("NER0046", "acetaminophen", "injection site reactions"): "co_mention",
    ("NER0046", "ibuprofen", "injection site reactions"): "co_mention",
    ("NER0048", "clozapine", "neutropenia"): "supported",
    ("NER0055", "clozapine", "severe neutropenia"): "supported",
    ("NER0063", "clozapine", "agranulocytosis"): "supported",
    ("NER0078", "clozapine", "neutropenia"): "supported",
    ("NER0081", "olanzapine", "agranulocytosis"): "co_mention",
    ("NER0081", "clozapine", "agranulocytosis"): "supported",
    ("NER0082", "clozapine", "agranulocytosis"): "supported",
    ("NER0083", "clozapine", "agranulocytosis"): "supported",
    ("NER0084", "lithium", "neutropenia"): "co_mention",
    ("NER0084", "clozapine", "neutropenia"): "supported",
    ("NER0085", "haloperidol", "neutropenic"): "supported",
    ("NER0085", "risperidone", "neutropenic"): "supported",
    ("NER0085", "clozapine", "neutropenic"): "unclear",
    ("NER0086", "clozapine", "myelotoxicity"): "supported",
    ("NER0086", "clozapine", "neutropenia"): "co_mention",
    ("NER0086", "clozapine", "agranulocytosis"): "co_mention",
    ("NER0086", "clozapine", "thrombocytopenia"): "co_mention",
    ("NER0087", "clozapine", "neutropenia"): "speculative",
    ("NER0087", "clozapine", "agranulocytosis"): "speculative",
    ("NER0088", "clozapine", "agranulocytosis"): "co_mention",
    ("NER0089", "clozapine", "neutropenia"): "supported",
    ("NER0089", "clozapine", "myelosuppression"): "supported",
    ("NER0090", "clozapine", "neutropenic"): "co_mention",
    ("NER0090", "clozapine", "agranulocytosis"): "unclear",
    ("NER0090", "clozapine", "intestinal hypomotility"): "supported",
    ("NER0090", "clozapine", "constipation"): "supported",
    ("NER0090", "clozapine", "intestinal obstruction"): "supported",
    ("NER0090", "clozapine", "bowel necrosis"): "supported",
    ("NER0090", "clozapine", "intra-abdominal sepsis"): "supported",
    ("NER0091", "clozapine", "neutropenia"): "supported",
    ("NER0092", "clozapine", "neutropenia"): "supported",
    ("NER0092", "clozapine", "leukopenia"): "supported",
    ("NER0093", "clozapine", "neutropenia"): "supported",
    ("NER0093", "clozapine", "hepatotoxicity"): "supported",
    ("NER0095", "clozapine", "neutropenia"): "supported",
    ("NER0096", "clozapine", "neutropenia"): "supported",
    ("NER0096", "clozapine", "leukopenia"): "supported",
    ("NER0096", "clozapine", "cardiac disorders"): "supported",
    ("NER0097", "clozapine", "neutropenia"): "negated",
    ("NER0098", "clozapine", "agranulocytosis"): "supported",
    ("NER0099", "clozapine", "neutropenia"): "speculative",
    ("NER0100", "clozapine", "neutropenia"): "supported",
    ("NER0101", "clozapine", "agranulocytosis"): "supported",
    ("NER0102", "clozapine", "neutropenia"): "supported",
    ("NER0102", "clozapine", "agranulocytosis"): "supported",
    ("NER0103", "clozapine", "neutropenia"): "unclear",
    ("NER0104", "clozapine", "neutropenia"): "supported",
    ("NER0104", "clozapine", "abnormal liver functions"): "co_mention",
    ("NER0104", "simvastatin", "neutropenia"): "co_mention",
    ("NER0104", "simvastatin", "abnormal liver functions"): "supported",
    ("NER0104", "atorvastatin", "neutropenia"): "co_mention",
    ("NER0104", "atorvastatin", "abnormal liver functions"): "supported",
    ("NER0105", "clozapine", "seizure"): "supported",
    ("NER0105", "clozapine", "myocarditis"): "supported",
    ("NER0105", "clozapine", "neutropenia"): "unclear",
    ("NER0105", "lithium", "seizure"): "speculative",
    ("NER0105", "lithium", "myocarditis"): "speculative",
    ("NER0105", "lithium", "neutropenia"): "negated",
    ("NER0106", "clozapine", "agranulocytosis"): "unclear",
    ("NER0106", "clozapine", "leukopenia"): "unclear",
    ("NER0107", "clozapine", "neutropenia"): "supported",
    ("NER0108", "clozapine", "neutropenia"): "co_mention",
    ("NER0109", "clozapine", "agranulocytosis"): "supported",
    ("NER0110", "clozapine", "agranulocytosis"): "supported",
    ("NER0111", "clozapine", "severe neutropenia"): "supported",
    ("NER0111", "clozapine", "seizures"): "supported",
    ("NER0111", "clozapine", "orthostasis"): "supported",
    ("NER0111", "clozapine", "myocarditis"): "supported",
    ("NER0111", "clozapine", "cardiomyopathy"): "supported",
    ("NER0111", "clozapine", "mitral valve prolapse"): "supported",
    ("NER0112", "clozapine", "neutropenia"): "supported",
    ("NER0113", "clozapine", "neutropenia"): "supported",
    ("NER0114", "clozapine", "neutropenia"): "supported",
    ("NER0114", "olanzapine", "neutropenia"): "supported",
    ("NER0115", "clozapine", "neutropenia"): "supported",
    ("NER0116", "clozapine", "neutropenia"): "supported",
    ("NER0117", "clozapine", "leukopenia"): "speculative",
    ("NER0117", "clozapine", "neutropenia"): "speculative",
    ("NER0117", "risperidone", "leukopenia"): "speculative",
    ("NER0117", "risperidone", "neutropenia"): "speculative",
    ("NER0117", "olanzapine", "leukopenia"): "speculative",
    ("NER0117", "olanzapine", "neutropenia"): "speculative",
    ("NER0117", "quetiapine", "leukopenia"): "speculative",
    ("NER0117", "quetiapine", "neutropenia"): "speculative",
    ("NER0118", "clozapine", "neutropenia"): "supported",
    ("NER0119", "clozapine", "neutropenia"): "supported",
    ("NER0120", "clozapine", "neutropenia"): "supported",
    ("NER0120", "clozapine", "agranulocytosis"): "supported",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_rows() -> list[dict[str, Any]]:
    source_rows = _read_csv(INPUT)
    result: list[dict[str, Any]] = []
    seen_annotations: set[tuple[str, str, str]] = set()
    for source in source_rows:
        gold_entities = json.loads(source["gold_entities_json"] or "[]")
        # Distinct normalized mention strings avoid multiplying an annotation
        # because the same word appears more than once in a sentence.
        drugs: dict[str, dict[str, Any]] = {}
        adrs: dict[str, dict[str, Any]] = {}
        for entity in gold_entities:
            if entity["label"] not in {"DRUG", "ADR"}:
                continue
            target = drugs if entity["label"] == "DRUG" else adrs
            target.setdefault(str(entity["text"]).casefold(), entity)

        for drug_key, drug in drugs.items():
            for adr_key, adr in adrs.items():
                annotation_key = (source["sample_id"], drug_key, adr_key)
                if annotation_key in seen_annotations:
                    continue
                seen_annotations.add(annotation_key)
                gold_status = GOLD.get(annotation_key)
                if gold_status is None:
                    raise ValueError(f"Missing first-pass gold label: {annotation_key}")
                model_entities = [
                    {**drug, "label": "DRUG"},
                    {**adr, "label": "ADR"},
                ]
                prediction = extract_sentence_relations(
                    source["sentence"], model_entities, use_case_study_lexicon=False
                )[0]
                if prediction["evidence_class"] == "co_mention_only":
                    predicted_status = "co_mention"
                elif prediction["assertion"] == "negated":
                    predicted_status = "negated"
                elif prediction["assertion"] == "speculative":
                    predicted_status = "speculative"
                else:
                    predicted_status = "supported"
                result.append(
                    {
                        "relation_id": f"{source['sample_id']}:{len(result) + 1:03d}",
                        "sample_id": source["sample_id"],
                        "sampling_stratum": source["sampling_stratum"],
                        "pmid": source["pmid"],
                        "drug": drug["text"],
                        "adr": adr["text"],
                        "sentence": source["sentence"],
                        "gold_status": gold_status,
                        "predicted_status": predicted_status,
                        "predicted_relation_cues": json.dumps(prediction["relation_cues"], ensure_ascii=False),
                        "predicted_context_cues": json.dumps(prediction["context_cues"], ensure_ascii=False),
                        "annotation_provenance": "assistant_first_pass_requires_independent_adjudication",
                        "annotation_notes": "",
                    }
                )
    if len(result) != len(GOLD):
        result_keys = {(r["sample_id"], r["drug"].casefold(), r["adr"].casefold()) for r in result}
        extra = sorted(set(GOLD) - result_keys)
        raise ValueError(f"Gold labels without a matching candidate: {extra}")
    return result


def main() -> None:
    rows = build_rows()
    _write_csv(
        OUTPUT,
        rows,
        [
            "relation_id", "sample_id", "sampling_stratum", "pmid", "drug", "adr",
            "sentence", "gold_status", "predicted_status", "predicted_relation_cues",
            "predicted_context_cues", "annotation_provenance", "annotation_notes",
        ],
    )
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["sampling_stratum"]] = counts.get(row["sampling_stratum"], 0) + 1
    print(f"Wrote {len(rows)} pair annotations to {OUTPUT}")
    print(json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    main()
