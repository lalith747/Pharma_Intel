from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dashboard.shared import load_dashboard_data, render_sidebar_metadata

summary, evidence, ranked, graph = load_dashboard_data()
render_sidebar_metadata(summary)

st.subheader("Evidence-level traceability")
event_terms = sorted(evidence["adr"].astype(str).unique())
chosen = st.selectbox("Adverse-event candidate", event_terms)
subset = evidence[evidence["adr"].astype(str).eq(chosen)].copy().reset_index(drop=True)
if subset.empty:
    st.info("No evidence rows for this term.")
else:
    counts = subset["relation_status"].value_counts().to_dict()
    st.caption(
        f"{len(subset)} sentence-level candidates · {subset['pmid'].nunique()} unique PMIDs · {counts}"
    )
    idx = st.selectbox(
        "Evidence record",
        list(range(len(subset))),
        format_func=lambda i: (
            f"{i + 1}. PMID {subset.iloc[i]['pmid']} · {subset.iloc[i]['relation_status']}"
        ),
    )
    row = subset.iloc[idx]
    st.markdown(f"### {row['title'] or 'PubMed article'}")
    st.markdown(
        f"PMID [{row['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{row['pmid']}/) · {row['publication_date']} · {row['journal']}"
    )
    st.markdown("**Supporting sentence**")
    st.info(row["evidence_sentence"])
    (c1, c2, c3) = st.columns(3)
    c1.metric("Model chemical label", str(row["drug_model_label"]))
    c2.metric("Model disease label", str(row["adr_model_label"]))
    c3.metric("Sentence status", str(row["relation_status"]))
    scores = []
    for name in ("drug_model_score", "adr_model_score"):
        try:
            scores.append(float(row[name]))
        except (TypeError, ValueError):
            scores.append(float("nan"))
    st.caption(
        f"NER token-classification scores: chemical {scores[0]:.3f}, disease {scores[1]:.3f}. These are model scores, not probabilities of a true clinical relationship."
    )
    st.write("Relation cues", row["relation_cues"] or "None; classified as co-mention only")
    st.write("Context cues", row["context_cues"] or "None detected by the lexical baseline")
    st.caption(
        "Assertion cues use a simple lexical window. Review the linked abstract before interpreting the relationship."
    )
    st.dataframe(
        subset[["pmid", "sentence_index", "drug_surface", "adr_surface", "relation_status"]],
        hide_index=True,
        width="stretch",
    )
