"""Free FDA safety communication feed for the SocialPulse dashboard page."""

from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import requests
import streamlit as st

FDA_SAFETY_PAGE = (
    "https://www.fda.gov/drugs/drug-safety-and-availability/drug-safety-communications"
)
FDA_HOST = "www.fda.gov"


class _SafetyTableParser(HTMLParser):
    """Extract date/title/link rows from the FDA page's communications table."""

    def __init__(self) -> None:
        super().__init__()
        self.in_row = False
        self.in_cell = False
        self.cell_text: list[str] = []
        self.cells: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.current_link: str | None = None
        self.current_link_text: list[str] = []
        self.rows: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "tr":
            self.in_row = True
            self.cells = []
            self.links = []
        elif tag in {"td", "th"} and self.in_row:
            self.in_cell = True
            self.cell_text = []
        elif tag == "a" and self.in_row:
            self.current_link = attributes.get("href") or ""
            self.current_link_text = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.cell_text.append(data)
        if self.current_link is not None:
            self.current_link_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.in_cell:
            self.cells.append(" ".join(" ".join(self.cell_text).split()))
            self.in_cell = False
        elif tag == "a" and self.current_link is not None:
            title = " ".join(" ".join(self.current_link_text).split())
            if self.current_link and title:
                self.links.append((self.current_link, title))
            self.current_link = None
            self.current_link_text = []
        elif tag == "tr" and self.in_row:
            if self.cells and self.links:
                href, title = self.links[0]
                self.rows.append({"date": self.cells[0], "title": title, "href": href})
            self.in_row = False
            self.in_cell = False


def _normalize_date(value: str) -> tuple[datetime, str]:
    for date_format in ("%m-%d-%Y", "%m-%d-%y", "%B %d, %Y"):
        try:
            date = datetime.strptime(value.strip(), date_format).replace(tzinfo=timezone.utc)
            return date, date.strftime("%d %b %Y")
        except ValueError:
            continue
    return datetime.min.replace(tzinfo=timezone.utc), value or "Date unavailable"


def parse_fda_safety_communications(html_text: str) -> list[dict[str, str]]:
    """Return linked FDA archive entries mentioning clozapine or Clozaril."""
    parser = _SafetyTableParser()
    parser.feed(html_text)
    records = []
    for row in parser.rows:
        if not any(term in row["title"].casefold() for term in ("clozapine", "clozaril")):
            continue
        url = urljoin(FDA_SAFETY_PAGE, row["href"])
        parsed_url = urlparse(url)
        host = parsed_url.hostname or ""
        if parsed_url.scheme != "https" or not (host == "fda.gov" or host.endswith(".fda.gov")):
            continue
        sort_date, display_date = _normalize_date(row["date"])
        records.append(
            {"title": row["title"], "date": display_date, "url": url, "_sort_date": sort_date}
        )
    records.sort(key=lambda item: item["_sort_date"], reverse=True)
    return [{key: value for key, value in item.items() if key != "_sort_date"} for item in records]


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def fetch_fda_clozapine_safety() -> dict:
    """Fetch the public FDA Drug Safety Communications archive, cached for 6h."""
    response = requests.get(
        FDA_SAFETY_PAGE,
        timeout=(4, 20),
        headers={"User-Agent": "PharmaIntel/1.0 (public safety communications display)"},
    )
    response.raise_for_status()
    articles = parse_fda_safety_communications(response.text)
    return {
        "articles": articles,
        "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
