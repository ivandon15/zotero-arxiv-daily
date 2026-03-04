import feedparser
from datetime import datetime, timedelta, timezone
from loguru import logger
from .base import BaseRetriever, register_retriever
from .sources import resolve_feed_url
from ..protocol import Paper


def _parse_date(entry) -> datetime | None:
    for field in ("published_parsed", "updated_parsed", "created_parsed"):
        t = entry.get(field)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _extract_authors(entry) -> list[str]:
    if "authors" in entry:
        return [a.get("name", "") for a in entry.authors if a.get("name")]
    if "author" in entry and entry.author:
        return [entry.author]
    if "dc_creator" in entry and entry.dc_creator:
        return [a.strip() for a in entry.dc_creator.split(",")]
    return []


def _extract_url(entry) -> str:
    if hasattr(entry, "links"):
        for link in entry.links:
            if link.get("type") != "application/pdf":
                return link.get("href", "")
    return entry.get("link", "")


@register_retriever("rss")
class RSSRetriever(BaseRetriever):
    def _retrieve_raw_papers(self) -> list:
        feeds: list[str] = list(self.retriever_config.feeds)
        since_days = getattr(self.retriever_config, "since_days", None)
        cutoff = None
        if since_days is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)

        raw = []
        for spec in feeds:
            url = resolve_feed_url(spec)
            logger.info(f"Fetching RSS feed: {url}")
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                logger.warning(f"Failed to parse feed {url}: {feed.bozo_exception}")
                continue
            for entry in feed.entries:
                if cutoff is not None:
                    pub = _parse_date(entry)
                    if pub is not None and pub < cutoff:
                        continue
                raw.append(entry)
        logger.info(f"Fetched {len(raw)} entries from {len(feeds)} feeds")
        if self.config.executor.debug:
            raw = raw[:10]
        return raw

    def retrieve_papers(self) -> list[Paper]:
        # Override to avoid ProcessPoolExecutor: FeedParserDict objects may not
        # survive pickling across process boundaries reliably.
        raw_papers = self._retrieve_raw_papers()
        logger.info("Processing papers...")
        papers = [self.convert_to_paper(entry) for entry in raw_papers]
        return [p for p in papers if p is not None]

    def convert_to_paper(self, entry) -> Paper | None:
        title = entry.get("title", "").strip()
        if not title:
            return None
        abstract = entry.get("summary", "") or entry.get("description", "")
        if "Abstract:" in abstract:
            abstract = abstract.split("Abstract:", 1)[-1].strip()
        url = _extract_url(entry)
        authors = _extract_authors(entry)
        return Paper(
            source="rss",
            title=title,
            authors=authors,
            abstract=abstract,
            url=url,
            pdf_url=None,
            full_text=None,
        )
