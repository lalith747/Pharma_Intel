"""Free, cached public-news retrieval for the SocialPulse dashboard page."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import requests
import streamlit as st

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"
NEWS_QUERIES = {
    "Clozapine coverage": "(clozapine OR clozaril)",
    "Blood-cell safety": (
        "(clozapine OR clozaril) "
        "(neutropenia OR agranulocytosis OR granulocytopenia OR leukopenia OR leucopenia)"
    ),
}
TIMESPANS = {"Past week": "1week", "Past month": "1month", "Past 3 months": "3months"}
MAX_RECORDS = 250


def _format_seen_date(value: str) -> str:
    if not value:
        return "Date unavailable"
    try:
        parsed = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        return parsed.strftime("%d %b %Y · %H:%M UTC")
    except ValueError:
        try:
            return parsedate_to_datetime(value).strftime("%d %b %Y · %H:%M UTC")
        except (TypeError, ValueError, OverflowError):
            return value


def _valid_http_url(value: object) -> str:
    url = str(value or "")
    parsed = urlparse(url)
    return url if parsed.scheme in {"http", "https"} and parsed.netloc else ""


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def fetch_public_news(topic: str, timespan: str) -> dict:
    """Fetch recent GDELT DOC article metadata; no key or user input is sent."""
    if topic not in NEWS_QUERIES or timespan not in TIMESPANS.values():
        raise ValueError("Unsupported SocialPulse news filter")
    response = requests.get(
        GDELT_DOC_API,
        params={
            "query": NEWS_QUERIES[topic],
            "mode": "artlist",
            "format": "json",
            "maxrecords": MAX_RECORDS,
            "timespan": timespan,
            "sort": "DateDesc",
        },
        timeout=(3, 12),
        headers={"User-Agent": "PharmaIntel/1.0 (public research news feed)"},
    )
    response.raise_for_status()
    payload = response.json()
    records = []
    for item in payload.get("articles", []):
        title = " ".join(str(item.get("title", "")).split())
        url = _valid_http_url(item.get("url"))
        if not title or not url:
            continue
        records.append(
            {
                "title": title,
                "url": url,
                "domain": str(item.get("domain", "")),
                "published": _format_seen_date(str(item.get("seendate", ""))),
                "language": str(item.get("language", "")),
                "source_country": str(item.get("sourcecountry", "")),
            }
        )
    return {
        "articles": records,
        "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source_limit": MAX_RECORDS,
    }
