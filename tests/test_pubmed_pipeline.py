from pharmaintel.data_acquisition.pubmed import (
    build_sentence_rows,
    deduplicate_records,
    normalize_pubmed_article,
    split_sentences,
)


def test_deduplicate_records_keeps_first_record_and_counts_duplicates():
    records = [
        {"pmid": "123", "title": "First"},
        {"pmid": "123", "title": "Duplicate"},
        {"pmid": "456", "title": "Second"},
        {"title": "Missing PMID"},
    ]

    unique, duplicate_count = deduplicate_records(records)

    assert [record["title"] for record in unique] == ["First", "Second"]
    assert duplicate_count == 1


def test_split_sentences_preserves_common_abbreviations_and_empty_values():
    text = "Clozapine can cause neutropenia, e.g. in vulnerable patients. It was reported."

    assert split_sentences(text) == [
        "Clozapine can cause neutropenia, e.g. in vulnerable patients.",
        "It was reported.",
    ]
    assert split_sentences("  \n ") == []


def test_split_sentences_does_not_split_respectively_abbreviation():
    text = "Perazine showed an incidence of 0.52‰, followed by quetiapine (15 cases resp. 1.42‰)."

    assert split_sentences(text) == [text]


def test_build_sentence_rows_retains_pmid_and_search_provenance():
    rows = build_sentence_rows(
        [{"pmid": "123", "abstract": "First sentence. Second sentence.", "title": "Title"}],
        query="clozapine AND neutropenia",
        retrieved_at="2026-11-18T12:00:00+00:00",
    )

    assert len(rows) == 2
    assert rows[0]["pmid"] == "123"
    assert rows[0]["sentence_index"] == 1
    assert rows[1]["sentence"] == "Second sentence."
    assert rows[0]["query"] == "clozapine AND neutropenia"
    assert rows[0]["retrieved_at_utc"] == "2026-11-18T12:00:00+00:00"


def test_normalize_pubmed_article_extracts_provenance_fields():
    article = {
        "MedlineCitation": {
            "PMID": "789",
            "Article": {
                "ArticleTitle": "A study",
                "Abstract": {"AbstractText": ["Abstract text."]},
                "Journal": {
                    "Title": "Example Journal",
                    "JournalIssue": {"PubDate": {"Year": "2024", "Month": "Jan"}},
                },
                "AuthorList": [{"ForeName": "A", "LastName": "Researcher"}],
            },
        },
        "PubmedData": {"ArticleIdList": []},
    }

    record = normalize_pubmed_article(article)

    assert record == {
        "pmid": "789",
        "record_type": "pubmed_article",
        "title": "A study",
        "abstract": "Abstract text.",
        "journal": "Example Journal",
        "publication_date": "2024 Jan",
        "doi": "",
        "authors": ["A Researcher"],
    }


def test_normalize_pubmed_book_article():
    record = normalize_pubmed_article(
        {
            "BookDocument": {
                "PMID": "33074616",
                "Book": {
                    "BookTitle": "Clozapine safety review",
                    "CollectionTitle": "Evidence reports",
                    "PubDate": {"Year": "2020", "Month": "01", "Day": "28"},
                    "AuthorList": [
                        [
                            {"ForeName": "A", "LastName": "Author"},
                            {"CollectiveName": "Review Group"},
                        ]
                    ],
                },
                "Abstract": {"AbstractText": ["Review abstract."]},
                "ArticleIdList": [],
            }
        }
    )

    assert record["pmid"] == "33074616"
    assert record["record_type"] == "pubmed_book"
    assert record["title"] == "Clozapine safety review"
    assert record["publication_date"] == "2020 01 28"
    assert record["authors"] == ["A Author", "Review Group"]
