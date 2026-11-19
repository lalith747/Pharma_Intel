"""Transparent, case-study-only lexical baseline for clozapine blood-event spans."""

from __future__ import annotations

import re

DRUG_TERMS = ("clozapine", "clozaril", "leponex")
ADR_TERMS = (
    "neutropenia", "neutropenic", "agranulocytosis", "granulocytopenia",
    "granulocytopenic", "leukopenia", "leucopenia",
)


def extract_case_study_entities(text: str) -> list[dict[str, object]]:
    """Find exact dictionary matches; this is not a general biomedical NER system."""
    entities: list[dict[str, object]] = []
    for label, terms in (("DRUG", DRUG_TERMS), ("ADR", ADR_TERMS)):
        for term in terms:
            for match in re.finditer(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE):
                entities.append(
                    {
                        "text": text[match.start() : match.end()],
                        "label": label,
                        "source_label": term,
                        "start": match.start(),
                        "end": match.end(),
                        "score": None,
                    }
                )
    entities.sort(key=lambda entity: (int(entity["start"]), int(entity["end"]), str(entity["label"])))
    return entities
