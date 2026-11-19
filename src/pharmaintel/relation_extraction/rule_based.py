"""Explainable sentence-level drug–ADR evidence baseline.

The output distinguishes explicit relation language from simple co-mention and
keeps assertion context separate. `causal_language` records wording in the
sentence; it is not a causal conclusion.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from pharmaintel.context_analysis.assertion import analyze_assertion
from pharmaintel.ner.rule_baseline import extract_case_study_entities


_RELATION_PATTERNS = (
    ("associated", re.compile(r"\b(?:associated|association|related|relationship|linked)\s+(?:with|to)\b", re.I)),
    ("risk_language", re.compile(r"\b(?:risk|increased\s+risk|risk\s+of)\b", re.I)),
    ("developed_after", re.compile(r"\b(?:developed|occurred|reported|presented|onset)\s+(?:after|following)\b", re.I)),
    ("event_after_exposure", re.compile(r"\b(?:after|following|during|upon)\s+(?:treatment|exposure|administration|use)\b", re.I)),
    ("causal_wording", re.compile(r"\b(?:caused|induced|triggered|resulted\s+in|led\s+to)\b", re.I)),
    ("adverse_effect_wording", re.compile(r"\b(?:adverse\s+effect|side\s+effect|toxicity)\b", re.I)),
)

_CAUSAL_LANGUAGE_PATTERN = re.compile(
    r"\b(?:caused|causing|induced|inducing|triggered|triggering|resulted\s+in|led\s+to)\b", re.I
)


def _entity_label(entity: dict[str, Any]) -> str | None:
    label = str(entity.get("label", "")).upper()
    if label in {"DRUG", "CHEMICAL", "MEDICATION"}:
        return "DRUG"
    if label in {"ADR", "DISEASE", "SIGN_SYMPTOM", "CLINICAL_EVENT"}:
        return "ADR"
    return None


def _valid_entities(text: str, entities: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    valid = []
    for entity in entities:
        if not isinstance(entity, dict) or _entity_label(entity) is None:
            continue
        try:
            start, end = int(entity["start"]), int(entity["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if 0 <= start < end <= len(text):
            normalized = dict(entity)
            normalized["start"], normalized["end"] = start, end
            normalized["label"] = _entity_label(entity)
            # Derive the surface form from offsets so evidence text stays exact.
            normalized["text"] = text[start:end]
            valid.append(normalized)
    return sorted(valid, key=lambda item: (item["start"], item["end"], item["label"]))


def _relation_cues(text: str) -> list[dict[str, Any]]:
    cues = []
    for cue_type, pattern in _RELATION_PATTERNS:
        cues.extend(
            {"type": cue_type, "text": match.group(), "start": match.start(), "end": match.end()}
            for match in pattern.finditer(text)
        )
    return sorted(cues, key=lambda cue: (cue["start"], cue["end"], cue["type"]))


def extract_sentence_relations(
    sentence: str,
    entities: Iterable[dict[str, Any]] | None = None,
    *,
    use_case_study_lexicon: bool = True,
) -> list[dict[str, Any]]:
    """Create evidence records for each in-sentence DRUG × ADR pair.

    If `entities` is omitted, the clozapine case-study lexicon is used when
    `use_case_study_lexicon` is true. Supply model predictions explicitly to
    run the same relation baseline over transformer-extracted mentions.
    """
    if entities is None:
        candidates = extract_case_study_entities(sentence) if use_case_study_lexicon else []
    else:
        candidates = list(entities)
    mentions = _valid_entities(sentence, candidates)
    drugs = [entity for entity in mentions if entity["label"] == "DRUG"]
    adrs = [entity for entity in mentions if entity["label"] == "ADR"]
    if not drugs or not adrs:
        return []

    relation_cues = _relation_cues(sentence)
    assertion = analyze_assertion(sentence, mentions)
    evidence_class = "explicit_relation_language" if relation_cues else "co_mention_only"
    causal_language = bool(_CAUSAL_LANGUAGE_PATTERN.search(sentence))
    records = []

    for drug in drugs:
        for adr in adrs:
            records.append(
                {
                    "drug": {"text": drug["text"], "start": drug["start"], "end": drug["end"]},
                    "adr": {"text": adr["text"], "start": adr["start"], "end": adr["end"]},
                    "evidence_sentence": sentence,
                    "evidence_class": evidence_class,
                    "relation_cues": relation_cues,
                    "assertion": assertion["assertion"],
                    "context_cues": assertion["cues"],
                    "causal_language": causal_language,
                    "causal_conclusion": None,
                    "method": "case_study_lexicon_and_relation_cues" if entities is None else "supplied_entities_and_relation_cues",
                }
            )
    return records
