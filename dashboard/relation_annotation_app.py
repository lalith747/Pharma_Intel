"""Blinded review screen for the PMID-disjoint relation holdout."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILE = ROOT / "data/annotated/relation_holdout_sample.csv"
LABELS = ["supported", "negated", "speculative", "co_mention", "unclear"]

st.set_page_config(page_title="PharmaIntel · Relation Review", page_icon="🧬", layout="wide")
st.title("PharmaIntel · Blinded Relation Review")
st.caption(
    "Review whether the sentence supports the displayed drug–event relation. Model outputs are hidden."
)

path = Path(st.sidebar.text_input("Annotation CSV", value=str(DEFAULT_FILE))).expanduser()
if not path.exists():
    st.error(f"Annotation file not found: {path}")
    st.stop()
frame = pd.read_csv(path, dtype={"pmid": str}, keep_default_na=False)
required = {
    "relation_id",
    "sampling_stratum",
    "pmid",
    "title",
    "sentence",
    "drug",
    "adr",
    "gold_status",
    "review_status",
    "annotation_notes",
}
if missing := required - set(frame.columns):
    st.error(f"Missing required columns: {', '.join(sorted(missing))}")
    st.stop()
leak_fields = {
    "predicted_status",
    "predicted_relation_cues",
    "predicted_context_cues",
    "model_score",
    "model_prediction",
}
if leak_fields & set(frame.columns):
    st.error("This review CSV contains prediction fields; refusing to show it as blinded.")
    st.stop()
if frame["pmid"].duplicated().any():
    st.error("Holdout must contain one candidate pair per PMID.")
    st.stop()
if frame.empty:
    st.info("No candidate pairs are available.")
    st.stop()

complete = frame["review_status"].eq("complete")
st.caption(
    f"{int(complete.sum())} complete · {len(frame) - int(complete.sum())} pending · strata shown separately in analysis"
)
if "relation_row" not in st.session_state:
    pending = frame.index[~complete].tolist()
    st.session_state.relation_row = pending[0] if pending else 0
st.session_state.relation_row = min(max(0, int(st.session_state.relation_row)), len(frame) - 1)

left, middle, right = st.columns([1, 4, 1])
with left:
    if st.button("← Previous", disabled=st.session_state.relation_row == 0):
        st.session_state.relation_row -= 1
        st.rerun()
with right:
    if st.button("Next →", disabled=st.session_state.relation_row >= len(frame) - 1):
        st.session_state.relation_row += 1
        st.rerun()
index = st.session_state.relation_row
row = frame.iloc[index]
with middle:
    st.markdown(
        f"**{row['relation_id']}** · {row['sampling_stratum']} · PMID [{row['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{row['pmid']}/) · {index + 1}/{len(frame)}"
    )
st.subheader(str(row["title"]) or "PubMed article")
st.markdown(f"**Candidate pair:** {row['drug']} → {row['adr']}")
st.markdown("**Evidence sentence**")
st.code(str(row["sentence"]), language=None, wrap_lines=True)
st.caption(
    "Choose the sentence-level relation status. “Supported” means the text asserts a relation; it does not establish clinical causality."
)

status_key = f"gold_{row['relation_id']}"
note_key = f"note_{row['relation_id']}"
current = str(row["gold_status"])
default_index = LABELS.index(current) if current in LABELS else 0
status = st.radio("Annotation", LABELS, index=default_index, horizontal=True, key=status_key)
notes = st.text_area("Review notes (optional)", value=str(row["annotation_notes"]), key=note_key)

if st.button("Save annotation", type="primary"):
    frame.at[index, "gold_status"] = status
    frame.at[index, "review_status"] = "complete"
    frame.at[index, "annotation_notes"] = notes
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    st.success("Saved.")
    if index < len(frame) - 1:
        st.session_state.relation_row = index + 1
    st.rerun()
