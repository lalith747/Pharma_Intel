from __future__ import annotations

import sys
from pathlib import Path

import networkx as nx
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dashboard.shared import load_dashboard_data, render_sidebar_metadata

summary, evidence, ranked, graph = load_dashboard_data()
render_sidebar_metadata(summary)

st.subheader("Evidence network")
st.caption(
    "Each sentence evidence node links the extracted chemical and disease candidates to its PMID. The graph encodes text evidence, not causality."
)
choices = ranked["adr"].astype(str).tolist()
adr = st.selectbox("Event term", choices)
drug_node = "drug:clozapine"
adr_node = "adr:" + str(adr).replace(" ", "_")
evidence_nodes = []
for node, data in graph.nodes(data=True):
    if data.get("node_type") != "evidence":
        continue
    neighbors = {target for (_, target) in graph.out_edges(node)}
    if drug_node in neighbors and adr_node in neighbors:
        evidence_nodes.append(node)
evidence_nodes = evidence_nodes[:80]
keep = {drug_node, adr_node, *evidence_nodes}
for node in evidence_nodes:
    keep.update(target for (_, target) in graph.out_edges(node))
subgraph = graph.subgraph(keep).copy()
if not evidence_nodes:
    st.info("No linked evidence nodes were found for this event term.")
else:
    positions = nx.spring_layout(subgraph, seed=17, k=0.8, iterations=60)
    (edge_x, edge_y) = ([], [])
    for source, target in subgraph.edges():
        (x0, y0) = positions[source]
        (x1, y1) = positions[target]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    traces = [
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line={"width": 0.7, "color": "#aab6c2"},
            hoverinfo="skip",
        )
    ]
    colors = {
        "drug": "#3572a5",
        "adverse_event": "#c35c55",
        "evidence": "#70a486",
        "publication": "#dfaa4c",
    }
    for kind, color in colors.items():
        nodes = [
            node for (node, data) in subgraph.nodes(data=True) if data.get("node_type") == kind
        ]
        traces.append(
            go.Scatter(
                x=[positions[node][0] for node in nodes],
                y=[positions[node][1] for node in nodes],
                mode="markers+text" if kind in {"drug", "adverse_event"} else "markers",
                text=[subgraph.nodes[node].get("label", node) for node in nodes]
                if kind in {"drug", "adverse_event"}
                else None,
                textposition="top center",
                marker={"size": 16 if kind in {"drug", "adverse_event"} else 8, "color": color},
                name=kind.replace("_", " "),
                hovertext=[
                    str(subgraph.nodes[node].get("label", node))
                    + "<br>"
                    + str(
                        subgraph.nodes[node].get("sentence", subgraph.nodes[node].get("title", ""))
                    )
                    for node in nodes
                ],
                hoverinfo="text",
            )
        )
    fig = go.Figure(traces)
    fig.update_layout(
        height=650,
        showlegend=True,
        margin={"l": 5, "r": 5, "t": 10, "b": 5},
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        f"Showing {len(evidence_nodes)} evidence sentences. Hover over evidence nodes for the sentence text."
    )
