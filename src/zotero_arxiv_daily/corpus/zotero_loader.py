from pyzotero import zotero
from ..protocol import CorpusPaper
from ..utils import glob_match
from datetime import datetime
import random
from loguru import logger


class ZoteroLoader:
    def __init__(self, user_id: str, api_key: str, include_path: str | None = None):
        self.user_id = user_id
        self.api_key = api_key
        self.include_path = include_path

    def load(self) -> list[CorpusPaper]:
        zot = zotero.Zotero(self.user_id, 'user', self.api_key)
        collections = zot.everything(zot.collections())
        collections = {c['key']: c for c in collections}

        corpus = zot.everything(zot.items(itemType='conferencePaper || journalArticle || preprint'))
        corpus = [c for c in corpus if c['data']['abstractNote'] != '']

        def get_collection_path(col_key: str) -> str:
            if p := collections[col_key]['data']['parentCollection']:
                return get_collection_path(p) + '/' + collections[col_key]['data']['name']
            else:
                return collections[col_key]['data']['name']

        for c in corpus:
            c['paths'] = [get_collection_path(col) for col in c['data']['collections']]

        logger.info(f"Fetched {len(corpus)} zotero papers")

        papers = [CorpusPaper(
            title=c['data']['title'],
            abstract=c['data']['abstractNote'],
            added_date=datetime.strptime(c['data']['dateAdded'], '%Y-%m-%dT%H:%M:%SZ'),
            paths=c['paths'],
        ) for c in corpus]

        if self.include_path:
            papers = [p for p in papers if any(glob_match(path, self.include_path) for path in p.paths)]
            logger.info(f"Filtered to {len(papers)} papers matching include_path")

        return papers
