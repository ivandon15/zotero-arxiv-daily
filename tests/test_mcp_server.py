from unittest.mock import MagicMock, patch
import pytest

def test_mcp_server_importable():
    from zotero_arxiv_daily import mcp_server
    assert hasattr(mcp_server, 'mcp')

def test_fetch_corpus_zotero():
    from zotero_arxiv_daily.mcp_server import fetch_corpus
    from zotero_arxiv_daily.protocol import CorpusPaper
    from datetime import datetime
    fake_paper = CorpusPaper(title="T", abstract="A", added_date=datetime.now(), paths=[])
    with patch('zotero_arxiv_daily.mcp_server.ZoteroLoader') as mock_cls:
        mock_cls.return_value.load.return_value = [fake_paper]
        result = fetch_corpus(corpus_source={"type": "zotero", "user_id": "1", "api_key": "k"})
    assert len(result) == 1
    assert result[0]["title"] == "T"

def test_fetch_corpus_pdf_dir():
    from zotero_arxiv_daily.mcp_server import fetch_corpus
    from zotero_arxiv_daily.protocol import CorpusPaper
    from datetime import datetime
    fake_paper = CorpusPaper(title="P", abstract="B", added_date=datetime.now(), paths=[])
    with patch('zotero_arxiv_daily.mcp_server.PDFLoader') as mock_cls:
        mock_cls.return_value.load.return_value = [fake_paper]
        result = fetch_corpus(corpus_source={"type": "pdf_dir", "path": "/some/dir"})
    assert len(result) == 1
    assert result[0]["title"] == "P"

def test_retrieve_papers_rss():
    from zotero_arxiv_daily.mcp_server import retrieve_papers
    from zotero_arxiv_daily.protocol import Paper
    fake_paper = Paper(source="rss", title="T", authors=[], abstract="A", url="https://x.com/1")
    with patch('zotero_arxiv_daily.mcp_server.RSSRetriever') as mock_cls:
        mock_cls.return_value.retrieve_papers.return_value = [fake_paper]
        result = retrieve_papers(feeds=["arxiv:cs.AI"], since_days=1)
    assert len(result) == 1
    assert result[0]["title"] == "T"
    assert result[0]["url"] == "https://x.com/1"

def test_list_sources_returns_dict():
    from zotero_arxiv_daily.mcp_server import list_sources
    result = list_sources()
    assert "arxiv" in result
    assert "nature" in result
