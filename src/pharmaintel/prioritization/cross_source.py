"""Arithmetic and weight-sensitivity audit for the exploratory case-study index.

This module reproduces the hand-designed index. It does not validate the index
against clinical outcomes or expert judgments.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

DEFAULT_WEIGHTS = {
    "faers_ebgm": 0.30,
    "literature_breadth": 0.25,
    "supported_relation_share": 0.25,
    "assertion_consistency": 0.20,
}


def audit_cross_source_index(
    signal: Mapping[str, Any], faers_reports: int, ebgm: float
) -> dict[str, Any]:
    """Recompute the project index and report transparent weight sensitivity.

    Inputs are descriptive literature counts and Assignment-provided FAERS
    values. The returned score is not an estimate of probability or risk.
    """
    count_keys = (
        "unique_pmid_count",
        "supported_pmid_count",
        "speculative_pmid_count",
        "negated_pmid_count",
        "mixed_pmid_count",
    )
    counts = {key: int(signal[key]) for key in count_keys}
    unique = counts["unique_pmid_count"]
    if unique <= 0 or faers_reports < 0 or ebgm < 0:
        raise ValueError("PMID count must be positive; FAERS inputs cannot be negative")
    categorized = sum(counts[key] for key in count_keys[1:])
    if categorized != unique:
        raise ValueError(
            f"Paper-status counts ({categorized}) do not reconcile to unique PMIDs ({unique})"
        )

    consistency = (
        counts["supported_pmid_count"]
        + 0.5 * counts["speculative_pmid_count"]
        + 0.5 * counts["mixed_pmid_count"]
    ) / unique
    stored_consistency = float(signal["consistency"])
    if not math.isclose(consistency, stored_consistency, rel_tol=0, abs_tol=1e-9):
        raise ValueError("Stored assertion consistency does not match paper-status counts")

    components = {
        "faers_ebgm": ebgm / (1 + ebgm),
        "literature_breadth": 1 - math.exp(-unique / 50),
        "supported_relation_share": counts["supported_pmid_count"] / unique,
        "assertion_consistency": consistency,
    }
    weights = dict(DEFAULT_WEIGHTS)
    weighted_score = 100 * sum(components[name] * weights[name] for name in weights)
    equal_weight_score = 100 * sum(components.values()) / len(components)

    leave_one_out = {}
    for omitted in components:
        remaining = [name for name in components if name != omitted]
        weight_total = sum(weights[name] for name in remaining)
        leave_one_out[omitted] = 100 * sum(
            components[name] * weights[name] / weight_total for name in remaining
        )

    component_min = min(components.values())
    component_max = max(components.values())
    faers_fixed_weight_bounds = {
        "minimum": 100
        * (weights["faers_ebgm"] * components["faers_ebgm"]
           + (1 - weights["faers_ebgm"])
           * min(v for k, v in components.items() if k != "faers_ebgm")),
        "maximum": 100
        * (weights["faers_ebgm"] * components["faers_ebgm"]
           + (1 - weights["faers_ebgm"])
           * max(v for k, v in components.items() if k != "faers_ebgm")),
    }

    return {
        "drug": str(signal.get("drug", "")),
        "adr": str(signal.get("adr", "")),
        "faers_reports_input": faers_reports,
        "faers_ebgm_input": ebgm,
        "paper_status_counts": counts,
        "paper_status_counts_reconcile": True,
        "stored_consistency": stored_consistency,
        "recomputed_consistency": consistency,
        "components": components,
        "weights": weights,
        "weighted_index": weighted_score,
        "equal_weight_index": equal_weight_score,
        "leave_one_component_out_indices": leave_one_out,
        "leave_one_component_out_range": {
            "minimum": min(leave_one_out.values()),
            "maximum": max(leave_one_out.values()),
        },
        "arbitrary_nonnegative_weights_range": {
            "minimum": 100 * component_min,
            "maximum": 100 * component_max,
        },
        "range_with_faers_weight_fixed_at_30_percent": faers_fixed_weight_bounds,
        "criterion_validated": False,
        "criterion_validation_reason": (
            "Only one pair has FAERS inputs; no independent expert labels or outcomes "
            "are available, and the relation holdout is still unannotated."
        ),
        "interpretation": "arithmetic and weight sensitivity audit only; not calibrated",
    }
