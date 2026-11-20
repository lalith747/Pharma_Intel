from unittest.mock import Mock, patch

import pytest

from dashboard.social_feed import fetch_public_news


def test_fetch_public_news_normalizes_records_and_limits_request():
    fetch_public_news.clear()
    response = Mock()
    response.json.return_value = {
        "articles": [
            {
                "title": " Clozapine safety update ",
                "url": "https://news.example/story",
                "domain": "news.example",
                "seendate": "20261119T120000Z",
                "language": "English",
                "sourcecountry": "United States",
            },
            {"title": "Unsafe link", "url": "javascript:alert(1)"},
        ]
    }
    with patch("dashboard.social_feed.requests.get", return_value=response) as get:
        feed = fetch_public_news("Blood-cell safety", "1month")

    response.raise_for_status.assert_called_once_with()
    assert len(feed["articles"]) == 1
    article = feed["articles"][0]
    assert article["title"] == "Clozapine safety update"
    assert article["published"] == "19 Nov 2026 · 12:00 UTC"
    assert article["url"] == "https://news.example/story"
    assert get.call_args.kwargs["params"]["maxrecords"] == 250
    assert get.call_args.kwargs["params"]["timespan"] == "1month"


def test_fetch_public_news_rejects_unknown_filter_without_request():
    fetch_public_news.clear()
    with (
        patch("dashboard.social_feed.requests.get") as get,
        pytest.raises(ValueError, match="Unsupported SocialPulse news filter"),
    ):
        fetch_public_news("Unknown topic", "1month")
    get.assert_not_called()
