from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from dashboard.shared import load_dashboard_data, render_sidebar_metadata

summary, evidence, ranked, graph = load_dashboard_data()
render_sidebar_metadata(summary)

status_counts = summary["case_study_relation_status_counts"]
st.markdown('<div class="eyebrow">Corpus snapshot · pinned model run</div>', unsafe_allow_html=True)
first_row = st.columns(2)
first_row[0].metric(
    "Sentences",
    f"{summary['sentences_scanned']:,}",
    help="Sentence-level corpus processed by the pinned biomedical NER model.",
)
first_row[1].metric(
    "PubMed records",
    f"{summary['unique_pmids_scanned']:,}",
    help="Unique publication identifiers in the current corpus snapshot.",
)
second_row = st.columns(2)
second_row[0].metric(
    "Pair candidates",
    f"{summary['case_study_pair_rows']:,}",
    help="Candidate clozapine–event sentence pairs. Pairs are not causal findings.",
)
second_row[1].metric(
    "ADR terms",
    f"{summary['case_study_signal_count']:,}",
    help="Terms ranked by the literature triage method.",
)
st.warning(
    "Research triage only. A literature mention or model score is not proof that a medicine caused an adverse reaction.",
    icon="⚕️",
)
(left, right) = st.columns([1.2, 1])
with left:
    st.subheader("Literature ranking")
    view = ranked.head(8).copy()
    view["label"] = view["adr"].astype(str)
    fig = go.Figure(
        go.Bar(
            x=view["priority_score"].astype(float),
            y=view["label"],
            orientation="h",
            marker_color="#930031",
            marker_line_color="#FFF2A7",
            marker_line_width=1,
        )
    )
    fig.update_layout(
        height=330,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, Aptos, sans-serif", "color": "#24151B"},
        yaxis={"autorange": "reversed", "gridcolor": "#F1E8E8"},
        xaxis_title="Evidence triage score",
        margin={"l": 10, "r": 10, "t": 10, "b": 35},
    )
    st.plotly_chart(fig, width="stretch")
with right:
    st.subheader("Relation context")
    labels = ["supported", "speculative", "negated", "co_mention"]
    values = [int(status_counts.get(label, 0)) for label in labels]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.62,
            marker_colors=["#930031", "#FFA500", "#BDE0FF", "#DDD3D7"],
            marker_line_color="white",
            marker_line_width=3,
        )
    )
    fig.update_layout(
        height=330,
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, Aptos, sans-serif", "color": "#24151B"},
        margin={"l": 0, "r": 0, "t": 10, "b": 10},
        legend={"orientation": "h", "y": -0.1},
    )
    st.plotly_chart(fig, width="stretch")
st.caption(
    f"Pinned {summary['model']['model_id']} · CPU inference: {summary['runtime_seconds']} s · model labels are candidate entity classes."
)
