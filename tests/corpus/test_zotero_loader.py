from unittest.mock import MagicMock, patch
from zotero_arxiv_daily.corpus.zotero_loader import ZoteroLoader

def test_load_returns_corpus_papers():
    loader = ZoteroLoader(user_id="123", api_key="key")
    mock_item = {
        'data': {
            'title': 'Test Paper',
            'abstractNote': 'An abstract.',
            'dateAdded': '2024-01-01T00:00:00Z',
            'collections': [],
        },
        'paths': [],
    }
    with patch('zotero_arxiv_daily.corpus.zotero_loader.zotero.Zotero') as mock_zot_cls:
        mock_zot = MagicMock()
        mock_zot_cls.return_value = mock_zot
        mock_zot.everything.side_effect = [[], [mock_item]]
        papers = loader.load()
    assert len(papers) == 1
    assert papers[0].title == 'Test Paper'
