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
    (
        "associated",
        re.compile(
            r"\b(?:associated|association|related|relationship|linked|correlated|correlation)\s+(?:with|to)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "risk_language",
        re.compile(
            r"\b(?:(?:increased|elevated|higher|reduced|lower)\s+)?risks?\s+(?:of|for|from)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "developed_after",
        re.compile(
            r"\b(?:develop(?:ed|s|ing)?|occur(?:red|s|ring)?|report(?:ed|s|ing)?|present(?:ed|s|ing)?|onset)\s+(?:after|following|with)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "event_after_exposure",
        re.compile(
            r"\b(?:after|following|during|upon)\s+(?:treatment|exposure|administration|use|therapy|intake)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "causal_wording",
        re.compile(
            r"\b(?:caus\w*|induc\w*|trigger\w*|result(?:ed|ing)?\s+in|lead\w*\s+to)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "adverse_effect_wording",
        re.compile(
            r"\b(?:adverse\s+(?:effect|reaction)|side\s+effect|toxicit\w*)\b", re.IGNORECASE
        ),
    ),
)

_CAUSAL_LANGUAGE_PATTERN = re.compile(
    r"\b(?:caus\w*|induc\w*|trigger\w*|result(?:ed|ing)?\s+in|lead\w*\s+to)\b", re.IGNORECASE
)
_CLAUSE_BOUNDARY = re.compile(r"[.!?;]|\b(?:whereas|however|nevertheless)\b", re.IGNORECASE)


def _entity_label(entity: dict[str, Any]) -> str | None:
    label = str(entity.get("label", "")).upper()
    if label in {"DRUG", "CHEMICAL", "MEDICATION"}:
        return "DRUG"
    if label in {"ADR", "DISEASE", "SIGN_SYMPTOM", "CLINICAL_EVENT"}:
        return "ADR"
    return None


def _valid_entities(text: str, entities: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    valid = []
    seen_spans: set[tuple[int, int, str]] = set()
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
            span_key = (start, end, normalized["label"])
            if span_key in seen_spans:
                continue
            seen_spans.add(span_key)
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


def _same_clause(text: str, left: int, right: int) -> bool:
    start, end = sorted((left, right))
    return _CLAUSE_BOUNDARY.search(text[start:end]) is None


def _assign_pair_cues(
    text: str,
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    cues: list[dict[str, Any]],
) -> dict[tuple[int, int], list[dict[str, Any]]]:
    """Assign each cue to its closest same-clause drug–ADR mention pair.

    A sentence-wide cue is no longer copied onto every pair. Cues tied between
    multiple candidate pairs are left unassigned to avoid inventing a link.
    The interval distance is an explicit lexical heuristic, not syntax parsing.
    """
    assigned: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for cue in cues:
        candidates: list[tuple[float, tuple[int, int]]] = []
        (cue["start"] + cue["end"]) / 2
        for drug, adr in pairs:
            if not (
                _same_clause(text, cue["start"], drug["start"])
                and _same_clause(text, cue["start"], adr["start"])
                and _same_clause(text, drug["start"], adr["start"])
            ):
                continue
            pair_start = min(drug["start"], adr["start"])
            pair_end = max(drug["end"], adr["end"])
            gap = max(pair_start - cue["end"], cue["start"] - pair_end, 0)
            # Inside-span cues dominate; outside-span cues must be very close.
            if gap > 24:
                continue
            span_length = pair_end - pair_start
            score = gap * 4 + span_length
            key = (drug["start"], adr["start"])
            candidates.append((score, key))
        if not candidates:
            continue
        candidates.sort()
        best_score = candidates[0][0]
        best = [key for score, key in candidates if score == best_score]
        if len(best) != 1:
            continue
        assigned.setdefault(best[0], []).append(cue)
    return assigned


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

    sentence_relation_cues = _relation_cues(sentence)
    mention_pairs = [(drug, adr) for drug in drugs for adr in adrs]
    pair_cues = _assign_pair_cues(sentence, mention_pairs, sentence_relation_cues)
    records = []

    for drug in drugs:
        for adr in adrs:
            relation_cues = pair_cues.get((drug["start"], adr["start"]), [])
            assertion = analyze_assertion(sentence, [drug, adr])
            records.append(
                {
                    "drug": {"text": drug["text"], "start": drug["start"], "end": drug["end"]},
                    "adr": {"text": adr["text"], "start": adr["start"], "end": adr["end"]},
                    "evidence_sentence": sentence,
                    "evidence_class": "explicit_relation_language"
                    if relation_cues
                    else "co_mention_only",
                    "relation_cues": relation_cues,
                    "assertion": assertion["assertion"],
                    "context_cues": assertion["cues"],
                    "causal_language": any(cue["type"] == "causal_wording" for cue in relation_cues)
                    and bool(_CAUSAL_LANGUAGE_PATTERN.search(sentence)),
                    "causal_conclusion": None,
                    "sentence_relation_cues": sentence_relation_cues,
                    "method": "case_study_lexicon_and_relation_cues"
                    if entities is None
                    else "supplied_entities_and_relation_cues",
                }
            )
    return records
