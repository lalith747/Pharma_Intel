from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dashboard.shared import load_dashboard_data, render_sidebar_metadata

summary, evidence, ranked, graph = load_dashboard_data()
render_sidebar_metadata(summary)

st.subheader("Model and method")
st.write(f"**Checkpoint:** `{summary['model']['model_id']}`")
st.write(f"**Pinned revision:** `{summary['model']['model_revision']}`")
st.write(f"**Raw label mapping:** {summary['model_label_mapping']}")
st.warning(summary["mapping_limit"])
st.markdown("**Relation method**")
st.write(
    "A pair-scoped lexical cue baseline assigns nearby association, risk, temporal, adverse-effect, or causal wording to the closest same-clause candidate pair. Negation and speculation use lexical cues. It does not use a trained relation classifier or syntactic scope parser."
)
st.markdown("**Evaluation status**")
st.write(summary["evaluation"])
st.write(
    "A separate 60-record PMID-disjoint blinded relation review sample can be generated with `python scripts/prepare_relation_holdout.py`. It needs human labels before held-out metrics can be calculated."
)
st.markdown("**Deployment mode**")
st.write(
    "This hosted interface reads pinned, precomputed corpus outputs. Run transformer inference locally or in Colab, then refresh the packaged dashboard data. The hosted app does not perform model inference per visitor."
)
st.markdown("**Score interpretation**")
st.write(summary["score_interpretation"])
