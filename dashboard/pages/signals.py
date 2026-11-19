from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dashboard.shared import load_dashboard_data, render_sidebar_metadata

summary, evidence, ranked, graph = load_dashboard_data()
render_sidebar_metadata(summary)

st.subheader("Literature signal ranking")
st.caption(
    "This score combines positive unique publications with assertion consistency. It is a transparent prioritization aid, not a causal probability."
)
ranked_view = ranked.copy()
max_literature_score = float(ranked_view["priority_score"].max())
ranked_view["relative_literature_index"] = (
    100 * ranked_view["priority_score"].astype(float) / max_literature_score
    if max_literature_score
    else 0
)
display_cols = [
    "drug",
    "adr",
    "unique_pmid_count",
    "supported_pmid_count",
    "speculative_pmid_count",
    "negated_pmid_count",
    "consistency",
    "priority_score",
    "relative_literature_index",
]
st.dataframe(
    ranked_view[display_cols],
    hide_index=True,
    width="stretch",
    column_config={
        "priority_score": st.column_config.NumberColumn("Literature score", format="%.3f"),
        "relative_literature_index": st.column_config.ProgressColumn(
            "Relative literature index", format="%.0f", min_value=0, max_value=100
        ),
        "consistency": st.column_config.ProgressColumn(
            "Assertion consistency", format="%.0%%", min_value=0, max_value=1
        ),
    },
)
st.caption(
    "Relative literature index is the current term’s literature score divided by the top score in this case-study run. It is a within-corpus comparison, not a safety confidence or a cross-source score."
)
st.markdown("#### Cross-source profile · clozapine–neutropenia")
st.markdown(
    "FAERS EBGM and literature evidence answer different questions. The index below is an **exploratory, uncalibrated evidence summary**, not a validated confidence or risk probability."
)
neut = ranked[ranked["adr"].astype(str).str.casefold().eq("neutropenia")]
if not neut.empty:
    signal = neut.iloc[0]
    (faers_count, ebgm) = (929, 50.81)
    faers_component = ebgm / (1 + ebgm)
    lit_component = 1 - __import__("math").exp(-float(signal["unique_pmid_count"]) / 50)
    relation_component = float(signal["supported_pmid_count"]) / max(
        float(signal["unique_pmid_count"]), 1
    )
    context_component = float(signal["consistency"])
    parts = {
        "FAERS EBGM": faers_component,
        "Literature breadth": lit_component,
        "Supported-relation share": relation_component,
        "Assertion consistency": context_component,
    }
    weights = {
        "FAERS EBGM": 0.3,
        "Literature breadth": 0.25,
        "Supported-relation share": 0.25,
        "Assertion consistency": 0.2,
    }
    index = 100 * sum(parts[k] * weights[k] for k in parts)
    (left, right) = st.columns([1, 1.25])
    with left:
        st.metric(
            "Exploratory cross-source index",
            f"{index:.1f} / 100",
            help="Weighted transformed evidence components; not validated or calibrated as a probability.",
        )
        st.caption(
            f"FAERS input: {faers_count:,} reports · EBGM {ebgm:.2f}. Source outcomes and reporting counts do not measure incidence."
        )
    with right:
        component_frame = pd.DataFrame(
            [
                {"Evidence component": k, "Component score": v, "Weight": weights[k]}
                for (k, v) in parts.items()
            ]
        )
        st.dataframe(
            component_frame,
            hide_index=True,
            width="stretch",
            column_config={
                "Component score": st.column_config.ProgressColumn(
                    min_value=0, max_value=1, format="%.0%%"
                ),
                "Weight": st.column_config.NumberColumn(format="%.0%%"),
            },
        )
    st.caption(
        "Transforms: EBGM/(1+EBGM); 1−exp(−unique PMIDs/50); supported PMIDs/unique relation PMIDs; existing assertion consistency. Weights: 30/25/25/20. The index is shown only for the exact clozapine–neutropenia pair; no unprovided FAERS values are imputed for other terms."
    )
    st.warning(
        "This hand-designed composite has not been calibrated against expert judgments or outcomes. Do not call it model confidence or use it for clinical decisions.",
        icon="⚠️",
    )
st.download_button(
    "Download ranked signal CSV",
    ranked.to_csv(index=False).encode("utf-8"),
    "transformer_case_study_signals.csv",
    "text/csv",
)
