import feedparser
from unittest.mock import patch
from omegaconf import OmegaConf
from zotero_arxiv_daily.retriever.rss_retriever import RSSRetriever

def _make_config(feeds: list[str], since_days=None):
    cfg = {
        "executor": {"source": ["rss"], "debug": False, "max_workers": 2},
        "source": {"rss": {"feeds": feeds}},
    }
    if since_days is not None:
        cfg["source"]["rss"]["since_days"] = since_days
    return OmegaConf.create(cfg)

def test_retriever_parses_atom_feed():
    cfg = _make_config(["https://fake.atom/feed"])
    parsed = feedparser.parse("tests/retriever/rss_atom_example.xml")

    with patch("feedparser.parse", return_value=parsed):
        retriever = RSSRetriever(cfg)
        papers = retriever.retrieve_papers()

    assert len(papers) == 2
    titles = {p.title for p in papers}
    assert "Test Paper One" in titles
    assert "Test Paper Two" in titles

def test_retriever_parses_rss2_feed():
    cfg = _make_config(["https://fake.rss/feed"])
    parsed = feedparser.parse("tests/retriever/rss2_example.xml")

    with patch("feedparser.parse", return_value=parsed):
        retriever = RSSRetriever(cfg)
        papers = retriever.retrieve_papers()

    assert len(papers) == 1
    assert papers[0].title == "Nature Paper One"
    assert papers[0].authors == ["Dave Brown"]

def test_retriever_resolves_named_source():
    cfg = _make_config(["arxiv:cs.AI"])
    parsed = feedparser.parse("tests/retriever/rss_atom_example.xml")

    with patch("feedparser.parse", return_value=parsed) as mock_parse:
        retriever = RSSRetriever(cfg)
        retriever.retrieve_papers()
        called_url = mock_parse.call_args[0][0]
    assert called_url == "https://rss.arxiv.org/atom/cs.AI"

def test_since_days_filters_old_entries():
    cfg = _make_config(["https://fake.atom/feed"], since_days=1)
    parsed = feedparser.parse("tests/retriever/rss_atom_example.xml")

    with patch("feedparser.parse", return_value=parsed):
        retriever = RSSRetriever(cfg)
        papers = retriever.retrieve_papers()

    assert papers == []

def test_paper_has_url_and_abstract():
    cfg = _make_config(["https://fake.atom/feed"])
    parsed = feedparser.parse("tests/retriever/rss_atom_example.xml")

    with patch("feedparser.parse", return_value=parsed):
        retriever = RSSRetriever(cfg)
        papers = retriever.retrieve_papers()

    p = next(p for p in papers if p.title == "Test Paper One")
    assert p.url == "https://arxiv.org/abs/2501.00001"
    assert "Abstract of paper one" in p.abstract
