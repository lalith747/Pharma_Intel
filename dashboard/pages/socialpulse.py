from __future__ import annotations

import html
import sys
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dashboard.shared import load_dashboard_data, render_sidebar_metadata
from dashboard.social_feed import FDA_SAFETY_PAGE, fetch_fda_clozapine_safety

summary, evidence, ranked, graph = load_dashboard_data()
render_sidebar_metadata(summary)

st.markdown('<div class="eyebrow">SOCIALPULSE · OFFICIAL SAFETY NEWS</div>', unsafe_allow_html=True)
st.title("Clozapine safety updates")
st.write(
    "Browse FDA safety communications that mention clozapine or Clozaril. The PubMed literature carousel remains available on the Overview page."
)
st.info(
    "This uses the FDA’s public safety communication archive—no sign-in, API key, or payment. X/Twitter posts are not included because official API reads are paid. This is an official-notice feed, not a complete social-media or general-news archive.",
    icon="📰",
)

if st.button("Refresh FDA notices"):
    fetch_fda_clozapine_safety.clear()
    st.rerun()

try:
    feed = fetch_fda_clozapine_safety()
except (requests.RequestException, ValueError) as exc:
    st.warning(
        "The FDA safety archive could not be reached. Try Refresh FDA notices in a little while; the rest of PharmaIntel is still available."
    )
    st.caption(f"Feed status: {type(exc).__name__}")
else:
    articles = feed["articles"]
    metric_cols = st.columns(2)
    metric_cols[0].metric("Clozapine notices found", f"{len(articles):,}")
    metric_cols[1].metric("Source", "FDA")
    st.caption(
        f"Checked {feed['retrieved_at']} · cached for six hours · "
        + "matched by clozapine/Clozaril in the FDA archive entry title."
    )

    if not articles:
        st.info(
            "No clozapine-related FDA communications were found in the current archive listing."
        )
    else:
        for index, article in enumerate(articles, start=1):
            with st.container(border=True):
                st.caption(
                    html.escape(f"FDA SAFETY COMMUNICATION  ·  {article['date']}  ·  {index:02d}")
                )
                st.markdown(f"### {html.escape(article['title'])}", unsafe_allow_html=True)
                st.link_button("Open FDA notice ↗", article["url"], key=f"fda-notice-{index}")
        st.caption(
            "This page only lists communications present in the FDA archive and matching the drug name in their titles. It does not establish that an adverse event was caused by clozapine."
        )
    st.link_button("Browse the full FDA Drug Safety Communications archive ↗", FDA_SAFETY_PAGE)


with st.expander("Advanced: screen an authorized CSV or text sample"):
    st.caption(
        "Optional local keyword screening. Uploaded rows stay within this app session and are not sent to the FDA notice feed."
    )
    uploaded = st.file_uploader(
        "CSV with a `text` column", type=["csv"], help="Optional columns: platform, date, post_id."
    )
    sample_text = st.text_area(
        "Or paste a small de-identified sample",
        height=100,
        placeholder="Example: I started clozapine and my blood count dropped…",
    )
    posts = pd.DataFrame()
    if uploaded is not None:
        try:
            posts = pd.read_csv(uploaded, keep_default_na=False)
            if "text" not in posts.columns:
                st.error("CSV needs a column named `text`.")
                posts = pd.DataFrame()
        except (pd.errors.ParserError, UnicodeDecodeError, ValueError, OSError) as exc:
            st.error(f"Could not read that CSV: {exc}")
            posts = pd.DataFrame()
    if sample_text.strip():
        pasted = pd.DataFrame(
            [
                {"text": line.strip(), "platform": "pasted sample"}
                for line in sample_text.splitlines()
                if line.strip()
            ]
        )
        posts = pd.concat([posts, pasted], ignore_index=True) if not posts.empty else pasted
    if not posts.empty:
        import re

        patterns = {
            "neutropenia": r"\bneutropeni\w*\b",
            "agranulocytosis": r"\bagranulocytosis\b",
            "granulocytopenia": r"\bgranulocytopeni\w*\b",
            "leukopenia": r"\bleukopeni\w*\b",
        }
        relation_pattern = r"\b(?:caus\w*|develop\w* after|after taking|side effect|adverse reaction|due to|trigger\w*)\b"
        analyzed = []
        for _, post in posts.iterrows():
            text = str(post.get("text", ""))
            events = [
                name
                for name, pattern in patterns.items()
                if re.search(pattern, text, re.IGNORECASE)
            ]
            relation = bool(re.search(relation_pattern, text, re.IGNORECASE))
            negated = bool(re.search(r"\b(?:no|not|never|without)\b", text, re.IGNORECASE))
            speculative = bool(
                re.search(r"\b(?:maybe|might|could|possibly|think|suspect)\b", text, re.IGNORECASE)
            )
            analyzed.append(
                {
                    "text": text,
                    "event_candidates": ", ".join(events) or "—",
                    "drug_mentioned": bool(re.search(r"\bclozapine\b", text, re.IGNORECASE)),
                    "screening_label": "negated cue"
                    if negated
                    else "speculative cue"
                    if speculative
                    else "relation wording"
                    if relation
                    else "co-mention",
                    "platform": post.get("platform", "unspecified"),
                }
            )
        results = pd.DataFrame(analyzed)
        hits = results[results["drug_mentioned"] & results["event_candidates"].ne("—")]
        metrics = st.columns(2)
        metrics[0].metric("Rows screened", f"{len(results):,}")
        metrics[1].metric("Drug + event mentions", f"{len(hits):,}")
        st.dataframe(hits if not hits.empty else results, hide_index=True, width="stretch")
        st.download_button(
            "Download screened rows",
            results.to_csv(index=False).encode("utf-8"),
            "socialpulse_screened_posts.csv",
            "text/csv",
        )
        st.caption(
            "Keyword/cue screening only; not a validated ADR classifier or causal assessment."
        )
