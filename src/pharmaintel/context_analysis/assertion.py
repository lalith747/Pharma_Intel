"""Rule-based assertion cues for biomedical evidence sentences.

This module labels linguistic context only. It does not determine whether a drug
causes an event, and its cue windows are a transparent baseline rather than a
validated negation/speculation scope model.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any


_NEGATION_PATTERNS = (
    re.compile(r"\bno\s+(?:significant\s+)?(?:association|relationship|evidence|link)\b", re.I),
    re.compile(r"\bnot\s+(?:associated|related|linked|caused)\b", re.I),
    re.compile(r"\b(?:did|does|do|was|were|is|are)\s+not\s+(?:develop|experience|cause|induce|associate)\w*\b", re.I),
    re.compile(r"\bwithout\s+(?:evidence\s+of\s+)?(?:developing\s+)?", re.I),
    re.compile(r"\babsence\s+of\b", re.I),
    re.compile(r"\bno\s+(?:cases?\s+of\s+)?", re.I),
)

_SPECULATION_PATTERNS = (
    re.compile(r"\bmay\b", re.I),
    re.compile(r"\bmight\b", re.I),
    re.compile(r"\bcould\b", re.I),
    re.compile(r"\bpossibly\b", re.I),
    re.compile(r"\bpossible\b", re.I),
    re.compile(r"\bpotential(?:ly)?\b", re.I),
    re.compile(r"\bsuspect(?:ed|s)?\b", re.I),
    re.compile(r"\bsuggest(?:s|ed|ing)?\b", re.I),
    re.compile(r"\b(?:cannot|can't)\s+exclude\b", re.I),
    re.compile(r"\b(?:appears|seems)\s+to\b", re.I),
    re.compile(r"\blikely\b", re.I),
)


def _collect_cues(text: str, patterns: Iterable[re.Pattern[str]], kind: str) -> list[dict[str, Any]]:
    cues: list[dict[str, Any]] = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            cues.append({"kind": kind, "text": match.group(), "start": match.start(), "end": match.end()})
    return sorted(cues, key=lambda cue: (cue["start"], cue["end"], cue["kind"]))


def analyze_assertion(text: str, entities: Iterable[dict[str, Any]] = ()) -> dict[str, Any]:
    """Return sentence-level negation/speculation cues and a conservative context label.

    A cue is considered local when it is within 80 characters of an entity span;
    if no valid spans are supplied, all sentence cues are returned. The simple
    character window can cross clause boundaries and must not be read as a scope
    model. Negation takes precedence over speculation when both cues are local.
    """
    spans = [
        (int(entity["start"]), int(entity["end"]))
        for entity in entities
        if isinstance(entity.get("start"), int) and isinstance(entity.get("end"), int)
    ]
    all_cues = _collect_cues(text, _NEGATION_PATTERNS, "negation")
    all_cues += _collect_cues(text, _SPECULATION_PATTERNS, "speculation")
    all_cues.sort(key=lambda cue: (cue["start"], cue["end"], cue["kind"]))

    if spans:
        cues = [
            cue for cue in all_cues
            if any(cue["end"] >= start - 80 and cue["start"] <= end + 80 for start, end in spans)
        ]
    else:
        cues = all_cues

    kinds = {cue["kind"] for cue in cues}
    if "negation" in kinds:
        label = "negated"
    elif "speculation" in kinds:
        label = "speculative"
    else:
        label = "affirmed_or_unmarked"

    return {
        "assertion": label,
        "negation_detected": "negation" in kinds,
        "speculation_detected": "speculation" in kinds,
        "cues": cues,
        "method": "lexical_cues_with_80_character_entity_window",
    }
