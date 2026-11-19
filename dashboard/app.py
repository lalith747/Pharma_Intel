"""PharmaIntel multi-page research dashboard entrypoint."""

from __future__ import annotations

import streamlit as st

from dashboard.shared import render_live_pubmed_banner

st.set_page_config(page_title="PharmaIntel | Safety Intelligence", page_icon="🧬", layout="wide")
st.markdown(
    """
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
[data-testid="stCaptionContainer"] { color:var(--muted); }
</style>
<div class="hero"><div class="hero-kicker">Pharmacovigilance intelligence · research prototype</div>
<h1>From biomedical evidence<br>to explainable safety insight.</h1>
<p>Traceable literature signals for clozapine and blood-cell events. Explore what the model found, inspect the source sentence, and see the limits alongside every score.</p></div>
""",
    unsafe_allow_html=True,
)

pages = [
    st.Page("pages/overview.py", title="Overview", icon="🏠", default=True),
    st.Page("pages/signals.py", title="Safety signals", icon="📊"),
    st.Page("pages/evidence.py", title="Evidence explorer", icon="🔎"),
    st.Page("pages/knowledge_graph.py", title="Knowledge graph", icon="🕸️"),
    st.Page("pages/socialpulse.py", title="SocialPulse", icon="📣"),
    st.Page("pages/methods.py", title="Methods & limits", icon="📘"),
]
render_live_pubmed_banner()
nav = st.navigation(pages, position="sidebar")
st.sidebar.markdown("### 🧬 PharmaIntel")
st.sidebar.caption("AI-powered safety intelligence")
nav.run()
