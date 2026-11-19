from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.shared import load_dashboard_data, render_sidebar_metadata

summary, evidence, ranked, graph = load_dashboard_data()
render_sidebar_metadata(summary)

st.subheader("SocialPulse · public-post research sandbox")
st.write(
    "Screen an already-authorized, de-identified CSV export for clozapine and blood-cell event mentions. No social platform is queried and no content is sent to an external API."
)
st.info(
    "Use only public, research-permitted, de-identified data. Do not upload usernames, profile links, private messages, or direct identifiers. Post-level mentions can reflect patients, caregivers, news, or jokes; they are not verified adverse-event reports.",
    icon="🔒",
)
uploaded = st.file_uploader(
    "Choose a CSV with a `text` column",
    type=["csv"],
    help="Optional columns: platform, date, post_id. Processing is session-only in this app.",
)
sample_text = st.text_area(
    "Or paste a small de-identified sample",
    height=130,
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

    adr_patterns = {
        "neutropenia": "\\bneutropeni\\w*\\b",
        "agranulocytosis": "\\bagranulocytosis\\b",
        "granulocytopenia": "\\bgranulocytopeni\\w*\\b",
        "leukopenia": "\\bleukopeni\\w*\\b",
    }
    rel_patterns = "\\b(?:caus\\w*|develop\\w* after|after taking|side effect|adverse reaction|due to|trigger\\w*)\\b"
    analyzed = []
    for _, post in posts.iterrows():
        text = str(post.get("text", ""))
        drug = bool(re.search("\\bclozapine\\b", text, re.IGNORECASE))
        events = [
            term
            for (term, pattern) in adr_patterns.items()
            if re.search(pattern, text, re.IGNORECASE)
        ]
        relation = bool(re.search(rel_patterns, text, re.IGNORECASE))
        negated = bool(re.search("\\b(?:no|not|never|without)\\b", text, re.IGNORECASE))
        speculative = bool(
            re.search("\\b(?:maybe|might|could|possibly|think|suspect)\\b", text, re.IGNORECASE)
        )
        status = (
            "negated cue"
            if negated
            else "speculative cue"
            if speculative
            else "relation wording"
            if relation
            else "co-mention"
        )
        analyzed.append(
            {
                "text": text,
                "event_candidates": ", ".join(events) or "—",
                "drug_mentioned": drug,
                "screening_label": status,
                "platform": post.get("platform", "unspecified"),
            }
        )
    results = pd.DataFrame(analyzed)
    hits = results[results["drug_mentioned"] & results["event_candidates"].ne("—")]
    m = st.columns(3)
    m[0].metric("Posts screened", f"{len(results):,}")
    m[1].metric("Drug + event mentions", f"{len(hits):,}")
    m[2].metric(
        "Posts with relation wording",
        f"{int(hits['screening_label'].eq('relation wording').sum()):,}",
    )
    st.dataframe(hits if not hits.empty else results, hide_index=True, width="stretch")
    st.download_button(
        "Download screened rows",
        results.to_csv(index=False).encode("utf-8"),
        "socialpulse_screened_posts.csv",
        "text/csv",
    )
    st.caption(
        "Screening uses transparent keyword and cue rules. It is not trained social-media ADR detection, sentiment analysis, or validated causal classification."
    )
else:
    st.markdown("**Input format**")
    st.code(
        'text,platform,date\n"I developed neutropenia after starting clozapine",public forum,2026-01-01',
        language="csv",
    )
st.markdown("**What SocialPulse currently does**")
st.write(
    "It provides a safe, source-separated way to prototype mention screening on authorized public data. Automated Reddit/X collection, API credentials, ethics review, deduplication, bot filtering, and human annotation are not implemented. Social data will not be mixed into PubMed or FAERS scores."
)
