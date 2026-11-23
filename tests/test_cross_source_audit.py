import pytest

from pharmaintel.prioritization import audit_cross_source_index


def example_signal():
    return {
        "drug": "clozapine",
        "adr": "neutropenia",
        "unique_pmid_count": 119,
        "supported_pmid_count": 93,
        "speculative_pmid_count": 18,
        "negated_pmid_count": 5,
        "mixed_pmid_count": 3,
        "consistency": (93 + 0.5 * 18 + 0.5 * 3) / 119,
    }


def test_cross_source_index_reproduces_displayed_value_and_checks_counts():
    audit = audit_cross_source_index(example_signal(), faers_reports=929, ebgm=50.81)

    assert audit["paper_status_counts_reconcile"] is True
    assert audit["recomputed_consistency"] == pytest.approx(0.8697478991596639)
    assert audit["components"]["faers_ebgm"] == pytest.approx(0.9806987068133565)
    assert audit["components"]["literature_breadth"] == pytest.approx(0.9074494224896568)
    assert audit["components"]["supported_relation_share"] == pytest.approx(0.7815126050420168)
    assert audit["weighted_index"] == pytest.approx(89.0399698758858)
    assert audit["criterion_validated"] is False


def test_weight_sensitivity_is_reported_without_calling_it_validation():
    audit = audit_cross_source_index(example_signal(), faers_reports=929, ebgm=50.81)

    assert audit["equal_weight_index"] == pytest.approx(88.48521583761735)
    assert audit["leave_one_component_out_range"]["minimum"] == pytest.approx(85.1700123878359)
    assert audit["leave_one_component_out_range"]["maximum"] == pytest.approx(92.66953966644718)
    assert audit["arbitrary_nonnegative_weights_range"]["minimum"] == pytest.approx(78.15126050420169)
    assert audit["arbitrary_nonnegative_weights_range"]["maximum"] == pytest.approx(98.06987068133564)


def test_inconsistent_status_counts_fail_loudly():
    signal = example_signal()
    signal["mixed_pmid_count"] = 2
    with pytest.raises(ValueError, match="do not reconcile"):
        audit_cross_source_index(signal, faers_reports=929, ebgm=50.81)


def test_negative_external_inputs_are_rejected():
    with pytest.raises(ValueError, match="cannot be negative"):
        audit_cross_source_index(example_signal(), faers_reports=929, ebgm=-1)
