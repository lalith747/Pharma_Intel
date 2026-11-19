"""Shared data loading and visual identity for PharmaIntel dashboard pages."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import networkx as nx
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
DATA = ROOT / "data/processed/pubmed"
DEPLOY_DATA = ROOT / "dashboard/data"

if (DATA / "transformer_case_study_evidence.csv").exists():
    SUMMARY_PATH = RESULTS / "transformer_corpus_summary.json"
    EVIDENCE_PATH = DATA / "transformer_case_study_evidence.csv"
    RANKED_PATH = RESULTS / "transformer_case_study_signals.csv"
    GRAPH_PATH = RESULTS / "pharmaintel_transformer_case_graph.graphml"
else:
    SUMMARY_PATH = DEPLOY_DATA / "transformer_corpus_summary.json"
    EVIDENCE_PATH = DEPLOY_DATA / "transformer_case_study_evidence.csv.gz"
    RANKED_PATH = DEPLOY_DATA / "transformer_case_study_signals.csv"
    GRAPH_PATH = DEPLOY_DATA / "pharmaintel_transformer_case_graph.graphml.gz"


@st.cache_data(show_spinner=False)
def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, keep_default_na=False)


@st.cache_resource(show_spinner=False)
def load_graph(path: str) -> nx.MultiDiGraph:
    if path.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return nx.read_graphml(handle)
    return nx.read_graphml(path)


def load_dashboard_data():
    missing = [
        path for path in (SUMMARY_PATH, EVIDENCE_PATH, RANKED_PATH, GRAPH_PATH) if not path.exists()
    ]
    if missing:
        st.warning(
            "Run `python scripts/run_transformer_corpus_ner.py` and `python scripts/prepare_dashboard_assets.py` to generate dashboard data."
        )
        st.code("\n".join(str(path.relative_to(ROOT)) for path in missing))
        st.stop()
    summary = load_json(str(SUMMARY_PATH))
    evidence = load_csv(str(EVIDENCE_PATH))
    ranked = load_csv(str(RANKED_PATH))
    graph = load_graph(str(GRAPH_PATH))
    if ranked.empty:
        st.info("The current corpus run produced no clozapine–blood-event candidate signals.")
        st.stop()
    return summary, evidence, ranked, graph


def render_sidebar_metadata(summary: dict) -> None:
    st.sidebar.markdown("---")
    st.sidebar.caption(
        f"Model: `{summary['model']['model_id']}`\n\n"
        f"Revision: `{summary['model']['model_revision'][:12]}`\n\n"
        f"Device: {summary['device'].upper()}"
    )
