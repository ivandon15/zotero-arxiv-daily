import pytest
from zotero_arxiv_daily.retriever.sources import resolve_feed_url, list_sources, register_source


def test_resolve_arxiv_with_category():
    url = resolve_feed_url("arxiv:cs.AI")
    assert url == "https://rss.arxiv.org/atom/cs.AI"


def test_resolve_arxiv_multi_category():
    url = resolve_feed_url("arxiv:cs.AI+cs.LG")
    assert url == "https://rss.arxiv.org/atom/cs.AI+cs.LG"


def test_resolve_named_source():
    url = resolve_feed_url("nature")
    assert "nature.com" in url


def test_resolve_raw_url():
    url = resolve_feed_url("https://example.com/feed.rss")
    assert url == "https://example.com/feed.rss"


def test_list_sources_returns_dict():
    sources = list_sources()
    assert "arxiv" in sources
    assert "nature" in sources
    assert "biorxiv" in sources


def test_register_custom_source(monkeypatch):
    monkeypatch.setattr("zotero_arxiv_daily.retriever.sources._custom", {})
    register_source("my_journal", "https://my.journal.com/rss")
    url = resolve_feed_url("my_journal")
    assert url == "https://my.journal.com/rss"


def test_resolve_unknown_source_raises():
    with pytest.raises(ValueError, match="Unknown source"):
        resolve_feed_url("nonexistent")


def test_resolve_arxiv_no_param_raises():
    with pytest.raises(ValueError, match="requires a parameter"):
        resolve_feed_url("arxiv")


def test_resolve_nature_with_param_raises():
    with pytest.raises(ValueError, match="does not support parameters"):
        resolve_feed_url("nature:something")
