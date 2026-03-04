from mcp.server.fastmcp import FastMCP
from omegaconf import OmegaConf
from .corpus import ZoteroLoader, PDFLoader
from .retriever.rss_retriever import RSSRetriever
from .retriever.sources import list_sources as _list_sources, register_source
from .reranker import get_reranker_cls
from .protocol import Paper, CorpusPaper
from .construct_email import render_email
from .utils import send_email
from openai import OpenAI
from loguru import logger
from typing import Any

mcp = FastMCP("zotero-arxiv-daily")


def _paper_to_dict(p: Paper) -> dict:
    return {
        "source": p.source,
        "title": p.title,
        "authors": p.authors,
        "abstract": p.abstract,
        "url": p.url,
        "pdf_url": p.pdf_url,
        "tldr": p.tldr,
        "affiliations": p.affiliations,
        "score": p.score,
    }


def _corpus_paper_to_dict(p: CorpusPaper) -> dict:
    return {
        "title": p.title,
        "abstract": p.abstract,
        "added_date": p.added_date.isoformat(),
        "paths": p.paths,
    }


@mcp.tool()
def fetch_corpus(corpus_source: dict) -> list[dict]:
    """Load corpus papers from Zotero or a local PDF directory.

    corpus_source examples:
      {"type": "zotero", "user_id": "...", "api_key": "...", "include_path": null}
      {"type": "pdf_dir", "path": "/path/to/pdfs"}
    """
    source_type = corpus_source.get("type")
    if source_type == "zotero":
        loader = ZoteroLoader(
            user_id=corpus_source["user_id"],
            api_key=corpus_source["api_key"],
            include_path=corpus_source.get("include_path"),
        )
    elif source_type == "pdf_dir":
        loader = PDFLoader(pdf_dir=corpus_source["path"])
    else:
        raise ValueError(f"Unknown corpus_source type: {source_type}. Use 'zotero' or 'pdf_dir'.")
    papers = loader.load()
    return [_corpus_paper_to_dict(p) for p in papers]


@mcp.tool()
def list_sources() -> dict[str, str]:
    """List all available named feed sources (builtin + custom registered).

    Returns a dict of {name: url_or_template}.
    For parameterized sources like arxiv, use "arxiv:cs.AI" syntax in retrieve_papers.
    """
    return _list_sources()


@mcp.tool()
def register_feed_source(name: str, url: str) -> str:
    """Register a custom named RSS/Atom feed source.

    After registering, use the name in retrieve_papers feeds list.
    Example: register_feed_source("my_journal", "https://journal.com/rss")
    """
    register_source(name, url)
    return f"Registered source '{name}' -> {url}"


@mcp.tool()
def retrieve_papers(feeds: list[str], since_days: int | None = 1) -> list[dict]:
    """Retrieve papers from RSS/Atom feeds.

    feeds: list of feed specs. Each can be:
      - A named source: "nature", "science", "cell", "pnas", etc.
      - A parameterized source: "arxiv:cs.AI", "arxiv:cs.AI+cs.LG", "biorxiv:neuroscience"
      - A raw URL: "https://any-rss-feed.com/feed.xml"
      Use list_sources() to see all available named sources.

    since_days: only return papers published in the last N days.
      Pass null to retrieve all available entries (for historical search).
    """
    cfg = OmegaConf.create({
        "executor": {"source": ["rss"], "debug": False, "max_workers": 10},
        "source": {
            "rss": {
                "feeds": feeds,
                **({"since_days": since_days} if since_days is not None else {}),
            }
        },
    })
    retriever = RSSRetriever(cfg)
    papers = retriever.retrieve_papers()
    return [_paper_to_dict(p) for p in papers]


@mcp.tool()
def rerank_papers(papers: list[dict], corpus: list[dict], reranker_config: dict = {}) -> list[dict]:
    """Rerank candidate papers against a corpus.

    papers: list of paper dicts (from retrieve_papers)
    corpus: list of corpus paper dicts (from fetch_corpus)
    reranker_config: {"type": "local"} or {"type": "api", "key": "...", "base_url": "...", "model": "..."}
    """
    from datetime import datetime
    corpus_objs = [CorpusPaper(
        title=c["title"],
        abstract=c["abstract"],
        added_date=datetime.fromisoformat(c["added_date"]),
        paths=c.get("paths", []),
    ) for c in corpus]

    paper_objs = [Paper(
        source=p.get("source", ""),
        title=p["title"],
        authors=p.get("authors", []),
        abstract=p.get("abstract", ""),
        url=p.get("url", ""),
        pdf_url=p.get("pdf_url"),
        full_text=p.get("full_text"),
    ) for p in papers]

    reranker_type = reranker_config.get("type", "local")
    cfg = OmegaConf.create({
        "reranker": {
            "local": {"model": "jinaai/jina-embeddings-v5-text-nano", "encode_kwargs": {"task": "retrieval", "prompt_name": "document"}},
            "api": {
                "key": reranker_config.get("key"),
                "base_url": reranker_config.get("base_url"),
                "model": reranker_config.get("model"),
            },
        }
    })
    reranker = get_reranker_cls(reranker_type)(cfg)
    ranked = reranker.rerank(paper_objs, corpus_objs)
    return [_paper_to_dict(p) for p in ranked]


@mcp.tool()
def generate_tldr(paper: dict, llm_config: dict) -> dict:
    """Generate a TLDR summary for a single paper.

    llm_config: {"api_key": "...", "base_url": "...", "generation_kwargs": {"model": "gpt-4o-mini"}, "language": "English"}
    """
    p = Paper(
        source=paper.get("source", ""),
        title=paper["title"],
        authors=paper.get("authors", []),
        abstract=paper.get("abstract", ""),
        url=paper.get("url", ""),
        pdf_url=paper.get("pdf_url"),
        full_text=paper.get("full_text"),
    )
    client = OpenAI(
        api_key=llm_config.get("api_key", ""),
        base_url=llm_config.get("base_url", "https://api.openai.com/v1"),
    )
    llm_params = {
        "generation_kwargs": llm_config.get("generation_kwargs", {"model": "gpt-4o-mini", "max_tokens": 512}),
        "language": llm_config.get("language", "English"),
    }
    p.generate_tldr(client, llm_params)
    return _paper_to_dict(p)


@mcp.tool()
def run_pipeline(
    corpus_source: dict,
    feeds: list[str],
    since_days: int | None = 1,
    reranker_config: dict = {},
    llm_config: dict = {},
    max_paper_num: int = 100,
    send_email_flag: bool = False,
    email_config: dict = {},
) -> list[dict]:
    """Run the full pipeline: fetch corpus, retrieve papers, rerank, generate TLDRs.

    Returns the ranked paper list. Optionally sends email if send_email_flag=True.

    corpus_source: {"type": "zotero", ...} or {"type": "pdf_dir", "path": "..."}
    feeds: list of feed specs, e.g. ["arxiv:cs.AI", "nature", "https://..."]
    since_days: only return papers published in the last N days (null for all)
    reranker_config: {"type": "local"} or {"type": "api", ...}
    llm_config: {"api_key": "...", "base_url": "...", "generation_kwargs": {"model": "..."}, "language": "English"}
    send_email_flag: if True, also send email using email_config
    email_config: {"sender": "...", "receiver": "...", "smtp_server": "...", "smtp_port": 465, "sender_password": "..."}
    """
    from tqdm import tqdm

    corpus_dicts = fetch_corpus(corpus_source)
    if not corpus_dicts:
        logger.warning("No corpus papers found.")
        return []

    paper_dicts = retrieve_papers(feeds, since_days)
    if not paper_dicts:
        logger.info("No new papers found.")
        return []

    ranked_dicts = rerank_papers(paper_dicts, corpus_dicts, reranker_config)
    ranked_dicts = ranked_dicts[:max_paper_num]

    from datetime import datetime
    client = OpenAI(
        api_key=llm_config.get("api_key", ""),
        base_url=llm_config.get("base_url", "https://api.openai.com/v1"),
    )
    llm_params = {
        "generation_kwargs": llm_config.get("generation_kwargs", {"model": "gpt-4o-mini", "max_tokens": 512}),
        "language": llm_config.get("language", "English"),
    }
    final_papers = []
    for pd in tqdm(ranked_dicts):
        p = Paper(
            source=pd.get("source", ""),
            title=pd["title"],
            authors=pd.get("authors", []),
            abstract=pd.get("abstract", ""),
            url=pd.get("url", ""),
            pdf_url=pd.get("pdf_url"),
            full_text=pd.get("full_text"),
            score=pd.get("score"),
        )
        p.generate_tldr(client, llm_params)
        p.generate_affiliations(client, llm_params)
        final_papers.append(p)

    if send_email_flag and email_config:
        html = render_email(final_papers)
        email_cfg = OmegaConf.create({"email": email_config})
        send_email(email_cfg, html)
        logger.info("Email sent.")

    return [_paper_to_dict(p) for p in final_papers]


if __name__ == "__main__":
    mcp.run()
