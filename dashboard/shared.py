"""Shared data loading and visual identity for PharmaIntel dashboard pages."""

from __future__ import annotations

import gzip
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx
import pandas as pd
import requests
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

PUBMED_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PUBMED_QUERY = (
    "clozapine[Title/Abstract] AND (neutropenia[Title/Abstract] OR "
    "neutropenic[Title/Abstract] OR agranulocytosis[Title/Abstract] OR "
    "granulocytopenia[Title/Abstract] OR leukopenia[Title/Abstract] OR "
    "leucopenia[Title/Abstract])"
)
ADR_TERM_PATTERNS = {
    "neutropenia": re.compile(r"\bneutropeni\w*\b", re.IGNORECASE),
    "agranulocytosis": re.compile(r"\bagranulocytosis\b", re.IGNORECASE),
    "granulocytopenia": re.compile(r"\bgranulocytopeni\w*\b", re.IGNORECASE),
    "leukopenia": re.compile(r"\bleukopeni\w*\b", re.IGNORECASE),
    "leucopenia": re.compile(r"\bleucopeni\w*\b", re.IGNORECASE),
}


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


def _xml_text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


def _pubmed_date(element: ET.Element | None) -> str:
    if element is None:
        return ""
    parts = [_xml_text(element.find(tag)) for tag in ("Year", "Month", "Day", "MedlineDate")]
    return " ".join(part for part in parts if part)


def parse_pubmed_articles(xml_content: bytes | str) -> list[dict[str, str]]:
    """Parse EFetch XML into plain, provenance-linked literature records."""
    root = ET.fromstring(xml_content)
    articles = []
    for record in root.findall(".//PubmedArticle"):
        article = record.find(".//Article")
        citation = record.find(".//MedlineCitation")
        pmid = _xml_text(citation.find("PMID") if citation is not None else None)
        title = _xml_text(article.find("ArticleTitle") if article is not None else None)
        journal = _xml_text(article.find(".//Journal/Title") if article is not None else None)
        published = _pubmed_date(
            article.find("Journal/JournalIssue/PubDate") if article is not None else None
        )
        if not published and article is not None:
            published = _pubmed_date(article.find(".//PubDate"))
        abstract_parts = []
        if article is not None:
            for section in article.findall(".//Abstract/AbstractText"):
                text = _xml_text(section)
                label = section.attrib.get("Label", "").strip()
                if text:
                    abstract_parts.append(f"{label}: {text}" if label else text)
        abstract = " ".join(abstract_parts)
        history = record.find(".//PubmedData/History")
        indexed_date = ""
        if history is not None:
            for date in history.findall("PubMedPubDate"):
                if date.attrib.get("PubStatus") == "entrez":
                    indexed_date = _pubmed_date(date)
                    break
        searchable = f"{title} {abstract}"
        mentioned_terms = [
            term for term, pattern in ADR_TERM_PATTERNS.items() if pattern.search(searchable)
        ]
        if pmid and title:
            articles.append(
                {
                    "pmid": pmid,
                    "title": title,
                    "journal": journal,
                    "publication_date": published or "Date not supplied",
                    "indexed_date": indexed_date or "Date not supplied",
                    "abstract": abstract,
                    "adr_terms_mentioned": ", ".join(mentioned_terms),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                }
            )
    return articles


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def fetch_latest_pubmed_updates() -> dict:
    """Fetch recent PubMed clozapine/blood-event records; shared cache lasts 6h."""
    params = {
        "db": "pubmed",
        "term": PUBMED_QUERY,
        "retmax": 3,
        "sort": "date_desc",
        "retmode": "json",
        "tool": "pharmaintel_dashboard",
    }
    search = requests.get(
        f"{PUBMED_EUTILS}/esearch.fcgi",
        params=params,
        timeout=(3, 6),
        headers={"User-Agent": "PharmaIntel/1.0 (PubMed literature display)"},
    )
    search.raise_for_status()
    result = search.json().get("esearchresult", {})
    ids = result.get("idlist", [])
    if not ids:
        return {
            "articles": [],
            "total_matches": int(result.get("count", 0)),
            "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        }

    fetched = requests.get(
        f"{PUBMED_EUTILS}/efetch.fcgi",
        params={
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "xml",
            "tool": "pharmaintel_dashboard",
        },
        timeout=(3, 8),
        headers={"User-Agent": "PharmaIntel/1.0 (PubMed literature display)"},
    )
    fetched.raise_for_status()
    return {
        "articles": parse_pubmed_articles(fetched.content),
        "total_matches": int(result.get("count", 0)),
        "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def render_live_pubmed_banner() -> None:
    """Show a browsable, cached PubMed literature carousel."""
    st.markdown('<div class="eyebrow">LIVE LITERATURE · PUBMED</div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.subheader("Latest clozapine literature")
        st.caption(
            "Recent PubMed records mentioning clozapine and selected blood-cell terms. "
            "Browse the cards; the shared feed refreshes every six hours."
        )
        try:
            updates = fetch_latest_pubmed_updates()
        except (requests.RequestException, ET.ParseError, ValueError) as exc:
            st.info(
                "The live PubMed feed is temporarily unavailable. The saved research results below are still available."
            )
            st.caption(f"Feed status: {type(exc).__name__}")
            return
        articles = updates["articles"]
        if not articles:
            st.info("No matching PubMed records were returned for the current search.")
            st.caption(f"Checked {updates['retrieved_at']} · {updates['total_matches']:,} matches")
            return
        if len(articles) > 1:
            previous, position, following = st.columns([1, 5, 1])
            current = st.session_state.get("pubmed_carousel_index", 0) % len(articles)
            with previous:
                if st.button("←", key="pubmed-carousel-prev", help="Previous article"):
                    st.session_state.pubmed_carousel_index = (current - 1) % len(articles)
                    st.rerun()
            with position:
                st.caption(f"ARTICLE {current + 1:02d} / {len(articles):02d}")
            with following:
                if st.button("→", key="pubmed-carousel-next", help="Next article"):
                    st.session_state.pubmed_carousel_index = (current + 1) % len(articles)
                    st.rerun()
        else:
            current = 0
            st.session_state.pubmed_carousel_index = 0

        article = articles[current]
        with st.container(border=True):
            st.markdown(f"#### {article['title']}")
            details = [
                value for value in (article["journal"], article["publication_date"]) if value
            ]
            st.caption(" · ".join(details) + f" · PMID {article['pmid']}")
            if article["adr_terms_mentioned"]:
                st.markdown(f"**Blood-cell terms found:** {article['adr_terms_mentioned']}")
            else:
                st.write("No selected blood-cell term found in the returned title/abstract.")
            if article["abstract"]:
                excerpt = article["abstract"][:620].rstrip()
                st.write(excerpt + ("…" if len(article["abstract"]) > 620 else ""))
            st.link_button("Open PubMed article ↗", article["url"])
        st.caption(
            f"Last fetched {updates['retrieved_at']} · {updates['total_matches']:,} matching records · "
            "NCBI E-utilities. Mentions are literature references, not validated safety alerts or proof of causality."
        )


def render_sidebar_metadata(summary: dict) -> None:
    st.sidebar.markdown("---")
    st.sidebar.caption(
        f"Model: `{summary['model']['model_id']}`\n\n"
        f"Revision: `{summary['model']['model_revision'][:12]}`\n\n"
        f"Device: {summary['device'].upper()}"
    )
