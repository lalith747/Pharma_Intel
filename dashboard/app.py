"""PharmaIntel research dashboard for the local, reproducible PubMed run."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

RESULTS = ROOT / "results"
DATA = ROOT / "data/processed/pubmed"
SUMMARY_PATH = RESULTS / "transformer_corpus_summary.json"
EVIDENCE_PATH = DATA / "transformer_case_study_evidence.csv"
RANKED_PATH = RESULTS / "transformer_case_study_signals.csv"
GRAPH_PATH = RESULTS / "pharmaintel_transformer_case_graph.graphml"

st.set_page_config(page_title="PharmaIntel · Safety Intelligence", page_icon="🧬", layout="wide")
st.title("PharmaIntel")
st.caption("AI-powered pharmacovigilance intelligence · PubMed case study: clozapine and blood-cell events")


@st.cache_data(show_spinner=False)
def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, keep_default_na=False)


@st.cache_resource(show_spinner=False)
def load_graph(path: str) -> nx.MultiDiGraph:
    return nx.read_graphml(path)


missing = [path for path in (SUMMARY_PATH, EVIDENCE_PATH, RANKED_PATH, GRAPH_PATH) if not path.exists()]
if missing:
    st.warning("Run `python scripts/run_transformer_corpus_ner.py` from the project root to generate dashboard data.")
    st.code("\n".join(str(path.relative_to(ROOT)) for path in missing))
    st.stop()

summary = load_json(str(SUMMARY_PATH))
evidence = load_csv(str(EVIDENCE_PATH))
ranked = load_csv(str(RANKED_PATH))
graph = load_graph(str(GRAPH_PATH))
if ranked.empty:
    st.info("The current corpus run produced no clozapine–blood-event candidate signals.")
    st.stop()

page = st.sidebar.radio("Explore", ["Overview", "Safety signals", "Evidence explorer", "Knowledge graph", "Method & limits"])
st.sidebar.markdown("---")
st.sidebar.caption(f"Model: `{summary['model']['model_id']}`\n\nRevision: `{summary['model']['model_revision'][:12]}`\n\nDevice: {summary['device'].upper()}")

if page == "Overview":
    status_counts = summary["case_study_relation_status_counts"]
    cols = st.columns(4)
    cols[0].metric("Sentences processed", f"{summary['sentences_scanned']:,}")
    cols[1].metric("PubMed records", f"{summary['unique_pmids_scanned']:,}")
    cols[2].metric("Candidate relation pairs", f"{summary['case_study_pair_rows']:,}")
    cols[3].metric("Ranked event terms", f"{summary['case_study_signal_count']:,}")
    st.info("These are model-generated literature candidates. They are not confirmed adverse reactions or clinical causal signals.")
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Highest-ranked literature candidates")
        view = ranked.head(8).copy()
        view["label"] = view["adr"].astype(str)
        fig = go.Figure(go.Bar(x=view["priority_score"].astype(float), y=view["label"], orientation="h", marker_color="#3c78a8"))
        fig.update_layout(height=330, yaxis={"autorange": "reversed"}, xaxis_title="Evidence triage score", margin={"l": 10, "r": 10, "t": 10, "b": 35})
        st.plotly_chart(fig, width="stretch")
    with right:
        st.subheader("Extracted relation context")
        labels = ["supported", "speculative", "negated", "co_mention"]
        values = [int(status_counts.get(label, 0)) for label in labels]
        fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.55, marker_colors=["#4b9b75", "#e5a642", "#c85a54", "#9aa6b2"]))
        fig.update_layout(height=330, margin={"l": 0, "r": 0, "t": 10, "b": 10}, legend={"orientation": "h", "y": -0.1})
        st.plotly_chart(fig, width="stretch")
    st.caption(f"Local CPU run · {summary['runtime_seconds']} seconds · cached model inference only. Labels describe sentence cues, not established causality.")

elif page == "Safety signals":
    st.subheader("Ranked case-study terms")
    st.caption("Score = log(1 + positive unique PMIDs) × assertion consistency. Use this for literature triage only.")
    display_cols = ["drug", "adr", "unique_pmid_count", "supported_pmid_count", "speculative_pmid_count", "negated_pmid_count", "consistency", "priority_score"]
    st.dataframe(ranked[display_cols], hide_index=True, width="stretch")
    st.download_button("Download ranked signal CSV", ranked.to_csv(index=False).encode("utf-8"), "transformer_case_study_signals.csv", "text/csv")

elif page == "Evidence explorer":
    st.subheader("Evidence-level traceability")
    event_terms = sorted(evidence["adr"].astype(str).unique())
    chosen = st.selectbox("Adverse-event candidate", event_terms)
    subset = evidence[evidence["adr"].astype(str).eq(chosen)].copy().reset_index(drop=True)
    if subset.empty:
        st.info("No evidence rows for this term.")
    else:
        counts = subset["relation_status"].value_counts().to_dict()
        st.caption(f"{len(subset)} sentence-level candidates · {subset['pmid'].nunique()} unique PMIDs · {counts}")
        idx = st.selectbox("Evidence record", list(range(len(subset))), format_func=lambda i: f"{i + 1}. PMID {subset.iloc[i]['pmid']} · {subset.iloc[i]['relation_status']}")
        row = subset.iloc[idx]
        st.markdown(f"### {row['title'] or 'PubMed article'}")
        st.markdown(f"PMID [{row['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{row['pmid']}/) · {row['publication_date']} · {row['journal']}")
        st.markdown("**Supporting sentence**")
        st.info(row["evidence_sentence"])
        c1, c2, c3 = st.columns(3)
        c1.metric("Model chemical label", str(row["drug_model_label"]))
        c2.metric("Model disease label", str(row["adr_model_label"]))
        c3.metric("Sentence status", str(row["relation_status"]))
        scores = []
        for name in ("drug_model_score", "adr_model_score"):
            try:
                scores.append(float(row[name]))
            except (TypeError, ValueError):
                scores.append(float("nan"))
        st.caption(f"NER token-classification scores: chemical {scores[0]:.3f}, disease {scores[1]:.3f}. These are model scores, not probabilities of a true clinical relationship.")
        st.write("Relation cues", row["relation_cues"] or "None; classified as co-mention only")
        st.write("Context cues", row["context_cues"] or "None detected by the lexical baseline")
        st.caption("Assertion cues use a simple lexical window. Review the linked abstract before interpreting the relationship.")
        st.dataframe(subset[["pmid", "sentence_index", "drug_surface", "adr_surface", "relation_status"]], hide_index=True, width="stretch")

elif page == "Knowledge graph":
    st.subheader("Evidence network")
    st.caption("Each sentence evidence node links the extracted chemical and disease candidates to its PMID. The graph encodes text evidence, not causality.")
    choices = ranked["adr"].astype(str).tolist()
    adr = st.selectbox("Event term", choices)
    drug_node = "drug:clozapine"
    adr_node = "adr:" + str(adr).replace(" ", "_")
    evidence_nodes = []
    for node, data in graph.nodes(data=True):
        if data.get("node_type") != "evidence":
            continue
        neighbors = {target for _, target in graph.out_edges(node)}
        if drug_node in neighbors and adr_node in neighbors:
            evidence_nodes.append(node)
    evidence_nodes = evidence_nodes[:80]
    keep = {drug_node, adr_node, *evidence_nodes}
    for node in evidence_nodes:
        keep.update(target for _, target in graph.out_edges(node))
    subgraph = graph.subgraph(keep).copy()
    if not evidence_nodes:
        st.info("No linked evidence nodes were found for this event term.")
    else:
        positions = nx.spring_layout(subgraph, seed=17, k=0.8, iterations=60)
        edge_x, edge_y = [], []
        for source, target in subgraph.edges():
            x0, y0 = positions[source]
            x1, y1 = positions[target]
            edge_x.extend([x0, x1, None]); edge_y.extend([y0, y1, None])
        traces = [go.Scatter(x=edge_x, y=edge_y, mode="lines", line={"width": 0.7, "color": "#aab6c2"}, hoverinfo="skip")]
        colors = {"drug": "#3572a5", "adverse_event": "#c35c55", "evidence": "#70a486", "publication": "#dfaa4c"}
        for kind, color in colors.items():
            nodes = [node for node, data in subgraph.nodes(data=True) if data.get("node_type") == kind]
            traces.append(go.Scatter(
                x=[positions[node][0] for node in nodes], y=[positions[node][1] for node in nodes],
                mode="markers+text" if kind in {"drug", "adverse_event"} else "markers",
                text=[subgraph.nodes[node].get("label", node) for node in nodes] if kind in {"drug", "adverse_event"} else None,
                textposition="top center", marker={"size": 16 if kind in {"drug", "adverse_event"} else 8, "color": color},
                name=kind.replace("_", " "),
                hovertext=[str(subgraph.nodes[node].get("label", node)) + "<br>" + str(subgraph.nodes[node].get("sentence", subgraph.nodes[node].get("title", ""))) for node in nodes],
                hoverinfo="text",
            ))
        fig = go.Figure(traces)
        fig.update_layout(height=650, showlegend=True, margin={"l": 5, "r": 5, "t": 10, "b": 5}, xaxis={"visible": False}, yaxis={"visible": False})
        st.plotly_chart(fig, width="stretch")
        st.caption(f"Showing {len(evidence_nodes)} evidence sentences. Hover over evidence nodes for the sentence text.")

else:
    st.subheader("Model and method")
    st.write(f"**Checkpoint:** `{summary['model']['model_id']}`")
    st.write(f"**Pinned revision:** `{summary['model']['model_revision']}`")
    st.write(f"**Raw label mapping:** {summary['model_label_mapping']}")
    st.warning(summary["mapping_limit"])
    st.markdown("**Relation method**")
    st.write("A pair-scoped lexical cue baseline assigns nearby association, risk, temporal, adverse-effect, or causal wording to the closest same-clause candidate pair. Negation and speculation use lexical cues. It does not use a trained relation classifier or syntactic scope parser.")
    st.markdown("**Evaluation status**")
    st.write(summary["evaluation"])
    st.write("A separate 60-record PMID-disjoint blinded relation review sample is prepared at `data/annotated/relation_holdout_sample.csv`. It needs human labels before held-out metrics can be calculated.")
    st.markdown("**Score interpretation**")
    st.write(summary["score_interpretation"])
