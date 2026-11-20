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
from dashboard.social_feed import MAX_RECORDS, NEWS_QUERIES, TIMESPANS, fetch_public_news

summary, evidence, ranked, graph = load_dashboard_data()
render_sidebar_metadata(summary)

st.markdown('<div class="eyebrow">SOCIALPULSE · PUBLIC NEWS</div>', unsafe_allow_html=True)
st.title("Clozapine news pulse")
st.write(
    "Browse recent public news mentioning clozapine, with a focused view for blood-cell safety coverage."
)
st.info(
    "Free, no sign-in or API key. X/Twitter posts are not included: the official X API charges for post reads. This feed uses GDELT-indexed news and does not claim to capture every article or social post.",
    icon="📰",
)

filters = st.columns([1.4, 1, 0.7])
with filters[0]:
    topic = st.selectbox("Coverage", list(NEWS_QUERIES))
with filters[1]:
    period = st.selectbox("Published within", list(TIMESPANS))
with filters[2]:
    st.write("")
    st.write("")
    refresh = st.button("Refresh feed", use_container_width=True)

if refresh:
    fetch_public_news.clear()
    st.rerun()

active_filters = (topic, TIMESPANS[period])
if st.session_state.get("socialpulse_filters") != active_filters:
    st.session_state.socialpulse_filters = active_filters
    st.session_state.socialpulse_page = 0

try:
    feed = fetch_public_news(topic, TIMESPANS[period])
except (requests.RequestException, ValueError) as exc:
    st.warning(
        "The public news service could not be reached. Try Refresh feed in a little while; the rest of PharmaIntel is still available."
    )
    st.caption(f"Feed status: {type(exc).__name__}")
else:
    articles = feed["articles"]
    metric_cols = st.columns(3)
    metric_cols[0].metric("Articles returned", f"{len(articles):,}")
    metric_cols[1].metric("Search window", period)
    metric_cols[2].metric("Source request cap", f"{MAX_RECORDS}")
    st.caption(
        f"GDELT DOC · retrieved {feed['retrieved_at']} · refreshes automatically every six hours. "
        "GDELT searches monitored online news from the past three months; this page requests at most 250 results."
    )

    if not articles:
        st.info("No matching news articles were returned for these filters.")
    else:
        page_size = 20
        page_count = (len(articles) + page_size - 1) // page_size
        page = min(st.session_state.socialpulse_page, page_count - 1)
        first = page * page_size
        last = min(first + page_size, len(articles))
        before, count, after = st.columns([1, 5, 1])
        with before:
            if st.button("← Previous", disabled=page == 0, key="socialpulse-prev"):
                st.session_state.socialpulse_page -= 1
                st.rerun()
        with count:
            st.caption(
                f"ARTICLES {first + 1}–{last} OF {len(articles)} · PAGE {page + 1}/{page_count}"
            )
        with after:
            if st.button("Next →", disabled=page >= page_count - 1, key="socialpulse-next"):
                st.session_state.socialpulse_page += 1
                st.rerun()

        for index, article in enumerate(articles[first:last], start=first + 1):
            with st.container(border=True):
                st.caption(
                    html.escape(
                        f"{index:03d}  ·  {article['published']}  ·  "
                        f"{article['domain'] or article['source_country'] or 'News source'}"
                    )
                )
                st.markdown(f"### {html.escape(article['title'])}", unsafe_allow_html=True)
                st.link_button(
                    "Open publisher article ↗", article["url"], key=f"news-{index}-{page}"
                )
        if len(articles) == MAX_RECORDS:
            st.caption(
                "The feed reached GDELT's 250-result request cap. Narrow the date window to browse a smaller slice; this count may be truncated."
            )
        st.caption(
            "GDELT returns article metadata and links, not full article text. Search matches are leads for human review—not verified ADR reports or evidence of causality."
        )


with st.expander("Advanced: screen an authorized CSV or text sample"):
    st.caption(
        "Optional local keyword screening. Uploaded rows stay within this app session and are not sent to the news search service."
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
