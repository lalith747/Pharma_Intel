from unittest.mock import Mock, patch

from dashboard.social_feed import fetch_fda_clozapine_safety, parse_fda_safety_communications

FDA_HTML = """
<table>
  <tr><th>Date</th><th>Title</th></tr>
  <tr><td>8-27-2025</td><td><a href="/drugs/example/clozapine-rems">FDA removes clozapine REMS</a></td></tr>
  <tr><td>1-28-2020</td><td><a href="/drugs/example/clozapine-constipation">FDA warns about constipation caused by clozapine</a></td></tr>
  <tr><td>1-1-2024</td><td><a href="/drugs/example/other">Safety update for another drug</a></td></tr>
  <tr><td>1-1-2024</td><td><a href="https://example.com/clozapine">External clozapine page</a></td></tr>
</table>
"""


def test_parse_fda_archive_filters_and_sorts_clozapine_notices():
    records = parse_fda_safety_communications(FDA_HTML)

    assert [item["date"] for item in records] == ["27 Aug 2025", "28 Jan 2020"]
    assert records[0]["title"] == "FDA removes clozapine REMS"
    assert records[0]["url"] == "https://www.fda.gov/drugs/example/clozapine-rems"
    assert len(records) == 2


def test_fda_feed_fetches_official_archive_and_returns_provenance():
    fetch_fda_clozapine_safety.clear()
    response = Mock(text=FDA_HTML)
    with patch("dashboard.social_feed.requests.get", return_value=response) as get:
        feed = fetch_fda_clozapine_safety()

    response.raise_for_status.assert_called_once_with()
    assert len(feed["articles"]) == 2
    assert feed["retrieved_at"].endswith("UTC")
    assert (
        get.call_args.args[0]
        == "https://www.fda.gov/drugs/drug-safety-and-availability/drug-safety-communications"
    )
