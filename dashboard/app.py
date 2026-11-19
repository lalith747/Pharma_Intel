"""PharmaIntel research dashboard for the local, reproducible PubMed run."""

from __future__ import annotations

import gzip
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
DEPLOY_DATA = ROOT / "dashboard/data"
# Select one complete data bundle. The hosted deployment does not contain the
# ignored local corpus under data/processed, so it must use dashboard/data for
# every artifact rather than mixing an older tracked results file with it.
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

st.set_page_config(page_title="PharmaIntel | Safety Intelligence", page_icon="🧬", layout="wide")
st.markdown("""
<style>
:root { --blue:#BDE0FF; --yellow:#FFF2A7; --orange:#FFA500; --wine:#930031; --ink:#24151B; --muted:#715D65; --paper:#FFFCF6; }
.stApp { background: radial-gradient(ellipse at 85% 0%, #fff2a73b 0, transparent 32%), var(--paper); color:var(--ink); }
html, body, [class*="css"] { font-family:Inter,'Aptos',system-ui,sans-serif; }
h1,h2,h3 { font-family:Inter,'Aptos',system-ui,sans-serif !important; letter-spacing:-.035em; color:var(--wine); }
div[data-testid="stSidebar"] { background:linear-gradient(180deg,var(--blue),#eaf5ff 52%,#fffaf0); border-right:1px solid #d8e5ef; }
div[data-testid="stSidebar"] p, div[data-testid="stSidebar"] label { color:var(--ink); }
div[data-testid="stMetric"] { background:#fff; border:1px solid #eadfe1; border-radius:18px; padding:18px 18px 14px; box-shadow:0 5px 20px #3900120a; }
div[data-testid="stMetricLabel"] { color:var(--muted); font-weight:600; }
div[data-testid="stMetricValue"] { color:var(--wine); font-family:Inter,'Aptos',system-ui,sans-serif; }
div[data-testid="stAlert"] { border-radius:14px; }
div[data-testid="stVerticalBlockBorderWrapper"] > div { border-radius:18px; border-color:#eadfe1; background:#fff; }
div.stButton > button, div.stDownloadButton > button { border-radius:12px; border:1px solid var(--wine); color:var(--wine); font-weight:700; }
div.stButton > button:hover, div.stDownloadButton > button:hover { background:var(--wine); color:white; border-color:var(--wine); }
[data-testid="stDataFrame"] { border:1px solid #eadfe1; border-radius:14px; overflow:hidden; }
.hero { padding:30px 32px; border-radius:24px; margin:.5rem 0 1.25rem; color:#fff; background:linear-gradient(115deg,#930031 0%,#650021 68%,#3a1020 100%); box-shadow:0 14px 40px #93003126; }
.hero-kicker { color:#FFF2A7; text-transform:uppercase; letter-spacing:.16em; font-size:.72rem; font-weight:700; }
.hero h1 { color:white!important; margin:.45rem 0 .4rem; font-size:2.45rem; }
.hero p { color:#fff3f6; font-size:1.02rem; margin:0; max-width:760px; }
.eyebrow { color:var(--wine); font-size:.72rem; letter-spacing:.12em; font-weight:800; text-transform:uppercase; }
.stCaption, [data-testid="stCaptionContainer"] { color:var(--muted); }
</style>
<div class="hero"><div class="hero-kicker">Pharmacovigilance intelligence · research prototype</div>
<h1>From biomedical evidence<br>to explainable safety insight.</h1>
<p>Traceable literature signals for clozapine and blood-cell events. Explore what the model found, inspect the source sentence, and see the limits alongside every score.</p></div>
""", unsafe_allow_html=True)


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


missing = [path for path in (SUMMARY_PATH, EVIDENCE_PATH, RANKED_PATH, GRAPH_PATH) if not path.exists()]
if missing:
    st.warning("Run `python scripts/run_transformer_corpus_ner.py` and `python scripts/prepare_dashboard_assets.py` to generate dashboard data.")
    st.code("\n".join(str(path.relative_to(ROOT)) for path in missing))
    st.stop()

summary = load_json(str(SUMMARY_PATH))
evidence = load_csv(str(EVIDENCE_PATH))
ranked = load_csv(str(RANKED_PATH))
graph = load_graph(str(GRAPH_PATH))
if ranked.empty:
    st.info("The current corpus run produced no clozapine–blood-event candidate signals.")
    st.stop()

st.sidebar.markdown("### 🧬 PharmaIntel")
st.sidebar.caption("AI-powered safety intelligence")
page = st.sidebar.radio("WORKSPACE", ["Overview", "Safety signals", "Evidence explorer", "Knowledge graph", "SocialPulse", "Methods & limits"])
st.sidebar.markdown("---")
st.sidebar.caption(f"Model: `{summary['model']['model_id']}`\n\nRevision: `{summary['model']['model_revision'][:12]}`\n\nDevice: {summary['device'].upper()}")

if page == "Overview":
    status_counts = summary["case_study_relation_status_counts"]
    st.markdown('<div class="eyebrow">Corpus snapshot · pinned model run</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    cols[0].metric("Sentences scanned", f"{summary['sentences_scanned']:,}", help="Sentence-level corpus processed by the pinned biomedical NER model.")
    cols[1].metric("PubMed records", f"{summary['unique_pmids_scanned']:,}", help="Unique publication identifiers in the current corpus snapshot.")
    cols[2].metric("Clozapine pairs", f"{summary['case_study_pair_rows']:,}", help="Candidate clozapine–event sentence pairs. Pairs are not causal findings.")
    cols[3].metric("Event terms", f"{summary['case_study_signal_count']:,}", help="Terms ranked by the literature triage method.")
    st.warning("Research triage only. A literature mention or model score is not proof that a medicine caused an adverse reaction.", icon="⚕️")
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Highest-ranked literature candidates")
        view = ranked.head(8).copy()
        view["label"] = view["adr"].astype(str)
        fig = go.Figure(go.Bar(x=view["priority_score"].astype(float), y=view["label"], orientation="h", marker_color="#930031", marker_line_color="#FFF2A7", marker_line_width=1))
        fig.update_layout(height=330, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={"family":"Inter, Aptos, sans-serif", "color":"#24151B"}, yaxis={"autorange": "reversed", "gridcolor":"#F1E8E8"}, xaxis_title="Evidence triage score", margin={"l": 10, "r": 10, "t": 10, "b": 35})
        st.plotly_chart(fig, width="stretch")
    with right:
        st.subheader("Extracted relation context")
        labels = ["supported", "speculative", "negated", "co_mention"]
        values = [int(status_counts.get(label, 0)) for label in labels]
        fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.62, marker_colors=["#930031", "#FFA500", "#BDE0FF", "#DDD3D7"], marker_line_color="white", marker_line_width=3))
        fig.update_layout(height=330, paper_bgcolor="rgba(0,0,0,0)", font={"family":"Inter, Aptos, sans-serif", "color":"#24151B"}, margin={"l": 0, "r": 0, "t": 10, "b": 10}, legend={"orientation": "h", "y": -0.1})
        st.plotly_chart(fig, width="stretch")
    st.caption(f"Pinned {summary['model']['model_id']} · CPU inference: {summary['runtime_seconds']} s · model labels are candidate entity classes.")

elif page == "Safety signals":
    st.subheader("Literature signal ranking")
    st.caption("This score combines positive unique publications with assertion consistency. It is a transparent prioritization aid, not a causal probability.")
    display_cols = ["drug", "adr", "unique_pmid_count", "supported_pmid_count", "speculative_pmid_count", "negated_pmid_count", "consistency", "priority_score"]
    st.dataframe(ranked[display_cols], hide_index=True, width="stretch", column_config={"priority_score":st.column_config.NumberColumn("Literature score", format="%.3f"), "consistency":st.column_config.ProgressColumn("Assertion consistency", format="%.0%%", min_value=0, max_value=1)})
    st.markdown("#### Cross-source profile · clozapine–neutropenia")
    st.markdown("FAERS EBGM and literature evidence answer different questions. The index below is an **exploratory, uncalibrated evidence summary**, not a validated confidence or risk probability.")
    neut = ranked[ranked["adr"].astype(str).str.casefold().eq("neutropenia")]
    if not neut.empty:
        signal = neut.iloc[0]
        # Assignment 2 source result: EBGM 50.81; Assignment 1 reports 929.
        # The transforms and weights are fixed, transparent and explicitly not calibrated.
        faers_count, ebgm = 929, 50.81
        faers_component = ebgm / (1 + ebgm)
        lit_component = 1 - __import__("math").exp(-float(signal["unique_pmid_count"]) / 50)
        relation_component = float(signal["supported_pmid_count"]) / max(float(signal["unique_pmid_count"]), 1)
        context_component = float(signal["consistency"])
        parts = {"FAERS EBGM": faers_component, "Literature breadth": lit_component, "Supported-relation share": relation_component, "Assertion consistency": context_component}
        weights = {"FAERS EBGM":.30, "Literature breadth":.25, "Supported-relation share":.25, "Assertion consistency":.20}
        index = 100 * sum(parts[k] * weights[k] for k in parts)
        left, right = st.columns([1,1.25])
        with left:
            st.metric("Exploratory cross-source index", f"{index:.1f} / 100", help="Weighted transformed evidence components; not validated or calibrated as a probability.")
            st.caption(f"FAERS input: {faers_count:,} reports · EBGM {ebgm:.2f}. Source outcomes and reporting counts do not measure incidence.")
        with right:
            component_frame = pd.DataFrame([{"Evidence component":k, "Component score":v, "Weight":weights[k]} for k,v in parts.items()])
            st.dataframe(component_frame, hide_index=True, width="stretch", column_config={"Component score":st.column_config.ProgressColumn(min_value=0,max_value=1,format="%.0%%"),"Weight":st.column_config.NumberColumn(format="%.0%%")})
        st.caption("Transforms: EBGM/(1+EBGM); 1−exp(−unique PMIDs/50); supported PMIDs/unique relation PMIDs; existing assertion consistency. Weights: 30/25/25/20. The index is shown only for the exact clozapine–neutropenia pair; no unprovided FAERS values are imputed for other terms.")
        st.warning("This hand-designed composite has not been calibrated against expert judgments or outcomes. Do not call it model confidence or use it for clinical decisions.", icon="⚠️")
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

elif page == "SocialPulse":
    st.subheader("SocialPulse · public-post research sandbox")
    st.write("Screen an already-authorized, de-identified CSV export for clozapine and blood-cell event mentions. No social platform is queried and no content is sent to an external API.")
    st.info("Use only public, research-permitted, de-identified data. Do not upload usernames, profile links, private messages, or direct identifiers. Post-level mentions can reflect patients, caregivers, news, or jokes; they are not verified adverse-event reports.", icon="🔒")
    uploaded = st.file_uploader("Choose a CSV with a `text` column", type=["csv"], help="Optional columns: platform, date, post_id. Processing is session-only in this app.")
    sample_text = st.text_area("Or paste a small de-identified sample", height=130, placeholder="Example: I started clozapine and my blood count dropped…")
    posts = pd.DataFrame()
    if uploaded is not None:
        try:
            posts = pd.read_csv(uploaded, keep_default_na=False)
            if "text" not in posts.columns:
                st.error("CSV needs a column named `text`.")
                posts = pd.DataFrame()
        except Exception as exc:
            st.error(f"Could not read that CSV: {exc}")
            posts = pd.DataFrame()
    if sample_text.strip():
        pasted = pd.DataFrame([{"text":line.strip(),"platform":"pasted sample"} for line in sample_text.splitlines() if line.strip()])
        posts = pd.concat([posts, pasted], ignore_index=True) if not posts.empty else pasted
    if not posts.empty:
        import re
        adr_patterns = {"neutropenia":r"\bneutropeni\w*\b", "agranulocytosis":r"\bagranulocytosis\b", "granulocytopenia":r"\bgranulocytopeni\w*\b", "leukopenia":r"\bleukopeni\w*\b"}
        rel_patterns = r"\b(?:caus\w*|develop\w* after|after taking|side effect|adverse reaction|due to|trigger\w*)\b"
        analyzed=[]
        for _, post in posts.iterrows():
            text=str(post.get("text", ""))
            drug=bool(re.search(r"\bclozapine\b",text,re.I))
            events=[term for term,pattern in adr_patterns.items() if re.search(pattern,text,re.I)]
            relation=bool(re.search(rel_patterns,text,re.I))
            negated=bool(re.search(r"\b(?:no|not|never|without)\b",text,re.I))
            speculative=bool(re.search(r"\b(?:maybe|might|could|possibly|think|suspect)\b",text,re.I))
            status="negated cue" if negated else "speculative cue" if speculative else "relation wording" if relation else "co-mention"
            analyzed.append({"text":text,"event_candidates":", ".join(events) or "—","drug_mentioned":drug,"screening_label":status,"platform":post.get("platform","unspecified")})
        results=pd.DataFrame(analyzed)
        hits=results[results["drug_mentioned"] & results["event_candidates"].ne("—")]
        m=st.columns(3);m[0].metric("Posts screened",f"{len(results):,}");m[1].metric("Drug + event mentions",f"{len(hits):,}");m[2].metric("Posts with relation wording",f"{int(hits['screening_label'].eq('relation wording').sum()):,}")
        st.dataframe(hits if not hits.empty else results,hide_index=True,width="stretch")
        st.download_button("Download screened rows",results.to_csv(index=False).encode("utf-8"),"socialpulse_screened_posts.csv","text/csv")
        st.caption("Screening uses transparent keyword and cue rules. It is not trained social-media ADR detection, sentiment analysis, or validated causal classification.")
    else:
        st.markdown("**Input format**")
        st.code("text,platform,date\n\"I developed neutropenia after starting clozapine\",public forum,2026-01-01",language="csv")
    st.markdown("**What SocialPulse currently does**")
    st.write("It provides a safe, source-separated way to prototype mention screening on authorized public data. Automated Reddit/X collection, API credentials, ethics review, deduplication, bot filtering, and human annotation are not implemented. Social data will not be mixed into PubMed or FAERS scores.")

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
    st.write("A separate 60-record PMID-disjoint blinded relation review sample can be generated with `python scripts/prepare_relation_holdout.py`. It needs human labels before held-out metrics can be calculated.")
    st.markdown("**Deployment mode**")
    st.write("This hosted interface reads pinned, precomputed corpus outputs. Run transformer inference locally or in Colab, then refresh the packaged dashboard data. The hosted app does not perform model inference per visitor.")
    st.markdown("**Score interpretation**")
    st.write(summary["score_interpretation"])
