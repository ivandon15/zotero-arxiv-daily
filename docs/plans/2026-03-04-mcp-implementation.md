# MCP Server Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expose the paper fetch + recommendation pipeline as an MCP server with 5 tools, while also supporting PDF folders as corpus source alongside Zotero.

**Architecture:** Extract corpus loading into a `corpus/` subpackage with `ZoteroLoader` and `PDFLoader`. Add `mcp_server.py` as a standalone entry point that wraps `Executor` methods as MCP tools. No changes to existing CLI or GitHub Action.

**Tech Stack:** `mcp` Python SDK (fastmcp style), `omegaconf.OmegaConf` for building configs from dicts, existing `extract_markdown_from_pdf`, `pyzotero`, `sentence-transformers`.

---

### Task 1: Add `mcp` dependency

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add dependency**

In `pyproject.toml` under `dependencies`, add:
```
"mcp>=1.0.0",
```

**Step 2: Install**

```bash
uv sync
```
Expected: resolves without error.

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add mcp dependency"
```

---

### Task 2: Create `corpus/` subpackage with `ZoteroLoader`

**Files:**
- Create: `src/zotero_arxiv_daily/corpus/__init__.py`
- Create: `src/zotero_arxiv_daily/corpus/zotero_loader.py`
- Create: `tests/corpus/test_zotero_loader.py`

**Step 1: Write the failing test**

`tests/corpus/test_zotero_loader.py`:
```python
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
```

**Step 2: Run to verify it fails**

```bash
uv run pytest tests/corpus/test_zotero_loader.py -v
```
Expected: FAIL with ImportError or ModuleNotFoundError.

**Step 3: Create `corpus/__init__.py`**

```python
from .zotero_loader import ZoteroLoader
from .pdf_loader import PDFLoader
```

(Leave `pdf_loader` import for Task 3 — add it then.)

For now just:
```python
from .zotero_loader import ZoteroLoader
```

**Step 4: Create `corpus/zotero_loader.py`**

Extract logic from `executor.py:22-43`:

```python
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
```

**Step 5: Run test to verify it passes**

```bash
uv run pytest tests/corpus/test_zotero_loader.py -v
```
Expected: PASS.

**Step 6: Commit**

```bash
git add src/zotero_arxiv_daily/corpus/ tests/corpus/
git commit -m "feat: add ZoteroLoader corpus subpackage"
```

---

### Task 3: Create `PDFLoader`

**Files:**
- Create: `src/zotero_arxiv_daily/corpus/pdf_loader.py`
- Modify: `src/zotero_arxiv_daily/corpus/__init__.py`
- Create: `tests/corpus/test_pdf_loader.py`

**Step 1: Write the failing test**

`tests/corpus/test_pdf_loader.py`:
```python
import os
from pathlib import Path
from unittest.mock import patch
from zotero_arxiv_daily.corpus.pdf_loader import PDFLoader

def test_load_pdfs(tmp_path):
    pdf_file = tmp_path / "my_paper.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 fake")  # fake pdf

    with patch('zotero_arxiv_daily.corpus.pdf_loader.extract_markdown_from_pdf', return_value="Some abstract text"):
        loader = PDFLoader(str(tmp_path))
        papers = loader.load()

    assert len(papers) == 1
    assert papers[0].title == "my_paper"
    assert papers[0].abstract == "Some abstract text"

def test_load_empty_dir(tmp_path):
    loader = PDFLoader(str(tmp_path))
    papers = loader.load()
    assert papers == []
```

**Step 2: Run to verify it fails**

```bash
uv run pytest tests/corpus/test_pdf_loader.py -v
```
Expected: FAIL with ImportError.

**Step 3: Create `corpus/pdf_loader.py`**

```python
import os
from datetime import datetime
from pathlib import Path
from loguru import logger
from ..protocol import CorpusPaper
from ..utils import extract_markdown_from_pdf


class PDFLoader:
    def __init__(self, pdf_dir: str):
        self.pdf_dir = pdf_dir

    def load(self) -> list[CorpusPaper]:
        pdf_files = list(Path(self.pdf_dir).glob("**/*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files in {self.pdf_dir}")
        papers = []
        for pdf_path in pdf_files:
            try:
                text = extract_markdown_from_pdf(str(pdf_path))
                mtime = datetime.fromtimestamp(os.path.getmtime(pdf_path))
                papers.append(CorpusPaper(
                    title=pdf_path.stem,
                    abstract=text[:2000],  # use first 2000 chars as abstract proxy
                    added_date=mtime,
                    paths=[str(pdf_path.relative_to(self.pdf_dir))],
                ))
            except Exception as e:
                logger.warning(f"Failed to process {pdf_path}: {e}")
        return papers
```

**Step 4: Update `corpus/__init__.py`**

```python
from .zotero_loader import ZoteroLoader
from .pdf_loader import PDFLoader
```

**Step 5: Run tests**

```bash
uv run pytest tests/corpus/ -v
```
Expected: all PASS.

**Step 6: Commit**

```bash
git add src/zotero_arxiv_daily/corpus/ tests/corpus/test_pdf_loader.py
git commit -m "feat: add PDFLoader corpus source"
```

---

### Task 4: Create `mcp_server.py`

**Files:**
- Create: `src/zotero_arxiv_daily/mcp_server.py`
- Create: `tests/test_mcp_server.py`

**Step 1: Write the failing test**

`tests/test_mcp_server.py`:
```python
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
```

**Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_mcp_server.py -v
```
Expected: FAIL with ImportError.

**Step 3: Create `mcp_server.py`**

```python
from mcp.server.fastmcp import FastMCP
from omegaconf import OmegaConf
from .corpus import ZoteroLoader, PDFLoader
from .retriever import get_retriever_cls
from .reranker import get_reranker_cls
from .protocol import Paper, CorpusPaper
from .construct_email import render_email
from .utils import send_email
from openai import OpenAI
from loguru import logger
from dataclasses import asdict
from typing import Any
import dataclasses

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


def _build_config(
    sources: list[str],
    reranker_config: dict,
    llm_config: dict,
    debug: bool = False,
    max_workers: int = 10,
    max_paper_num: int = 100,
) -> Any:
    """Build an OmegaConf config compatible with existing retrievers/rerankers."""
    source_cfg = {s: {} for s in ["arxiv", "biorxiv", "medrxiv"]}
    # merge caller-provided source config
    for s in sources:
        if s in reranker_config.get("source_config", {}):
            source_cfg[s] = reranker_config["source_config"][s]

    cfg = OmegaConf.create({
        "executor": {
            "source": sources,
            "reranker": reranker_config.get("type", "local"),
            "debug": debug,
            "max_workers": max_workers,
            "max_paper_num": max_paper_num,
            "send_empty": False,
        },
        "source": source_cfg,
        "reranker": reranker_config.get("reranker_params", {
            "local": {"model": "jinaai/jina-embeddings-v5-text-nano", "encode_kwargs": {"task": "retrieval", "prompt_name": "document"}},
            "api": {"key": None, "base_url": None, "model": None},
        }),
        "llm": {
            "api": {"key": llm_config.get("api_key", ""), "base_url": llm_config.get("base_url", "https://api.openai.com/v1")},
            "generation_kwargs": llm_config.get("generation_kwargs", {"max_tokens": 16384, "model": "gpt-4o-mini"}),
            "language": llm_config.get("language", "English"),
        },
    })
    return cfg


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
def retrieve_papers(sources: list[str], source_config: dict = {}) -> list[dict]:
    """Retrieve new papers from arxiv/biorxiv/medrxiv.

    sources: e.g. ["arxiv", "biorxiv"]
    source_config: per-source config, e.g. {"arxiv": {"category": ["cs.AI", "cs.LG"]}}
    """
    cfg = OmegaConf.create({
        "executor": {"source": sources, "debug": False, "max_workers": 10},
        "source": {
            "arxiv": source_config.get("arxiv", {"category": None}),
            "biorxiv": source_config.get("biorxiv", {"category": None}),
            "medrxiv": source_config.get("medrxiv", {"category": None}),
        },
    })
    all_papers = []
    for source in sources:
        retriever = get_retriever_cls(source)(cfg)
        papers = retriever.retrieve_papers()
        all_papers.extend(papers)
    return [_paper_to_dict(p) for p in all_papers]


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
    from .protocol import Paper as PaperObj
    p = PaperObj(
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
    sources: list[str],
    source_config: dict = {},
    reranker_config: dict = {},
    llm_config: dict = {},
    max_paper_num: int = 100,
    send_email_flag: bool = False,
    email_config: dict = {},
) -> list[dict]:
    """Run the full pipeline: fetch corpus, retrieve papers, rerank, generate TLDRs.

    Returns the ranked paper list. Optionally sends email if send_email_flag=True.

    corpus_source: {"type": "zotero", ...} or {"type": "pdf_dir", "path": "..."}
    sources: ["arxiv"], ["biorxiv"], ["arxiv", "medrxiv"], etc.
    source_config: {"arxiv": {"category": ["cs.AI"]}, ...}
    reranker_config: {"type": "local"} or {"type": "api", ...}
    llm_config: {"api_key": "...", "base_url": "...", "generation_kwargs": {"model": "..."}, "language": "English"}
    send_email_flag: if True, also send email using email_config
    email_config: {"sender": "...", "receiver": "...", "smtp_server": "...", "smtp_port": 465, "sender_password": "..."}
    """
    from tqdm import tqdm

    # 1. Fetch corpus
    corpus_dicts = fetch_corpus(corpus_source)
    if not corpus_dicts:
        logger.warning("No corpus papers found.")
        return []

    # 2. Retrieve papers
    paper_dicts = retrieve_papers(sources, source_config)
    if not paper_dicts:
        logger.info("No new papers found.")
        return []

    # 3. Rerank
    ranked_dicts = rerank_papers(paper_dicts, corpus_dicts, reranker_config)
    ranked_dicts = ranked_dicts[:max_paper_num]

    # 4. Generate TLDRs and affiliations
    from datetime import datetime
    from .protocol import Paper as PaperObj
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
        p = PaperObj(
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

    # 5. Optionally send email
    if send_email_flag and email_config:
        html = render_email(final_papers)
        email_cfg = OmegaConf.create({"email": email_config})
        send_email(email_cfg, html)
        logger.info("Email sent.")

    return [_paper_to_dict(p) for p in final_papers]


if __name__ == "__main__":
    mcp.run()
```

**Step 4: Run tests**

```bash
uv run pytest tests/test_mcp_server.py -v
```
Expected: all PASS.

**Step 5: Commit**

```bash
git add src/zotero_arxiv_daily/mcp_server.py tests/test_mcp_server.py
git commit -m "feat: add MCP server with 5 tools"
```

---

### Task 5: Add MCP entry point to `pyproject.toml`

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add script entry point**

In `pyproject.toml` under `[project]`, add:
```toml
[project.scripts]
zotero-arxiv-mcp = "zotero_arxiv_daily.mcp_server:mcp.run"
```

**Step 2: Sync and verify**

```bash
uv sync
uv run zotero-arxiv-mcp --help
```
Expected: MCP server help output (or it starts listening).

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add mcp server script entry point"
```

---

### Task 6: Update `Executor` to use `ZoteroLoader` (cleanup)

**Files:**
- Modify: `src/zotero_arxiv_daily/executor.py`

**Step 1: Replace inline zotero logic with `ZoteroLoader`**

In `executor.py`, replace `fetch_zotero_corpus` and `filter_corpus` methods with:

```python
from .corpus import ZoteroLoader

# in __init__, no change needed

def fetch_zotero_corpus(self) -> list[CorpusPaper]:
    loader = ZoteroLoader(
        user_id=self.config.zotero.user_id,
        api_key=self.config.zotero.api_key,
        include_path=self.config.zotero.include_path,
    )
    return loader.load()

def filter_corpus(self, corpus: list[CorpusPaper]) -> list[CorpusPaper]:
    return corpus  # filtering now done inside ZoteroLoader
```

**Step 2: Run existing tests**

```bash
uv run pytest tests/ -v --ignore=tests/utils
```
Expected: all PASS (no regressions).

**Step 3: Commit**

```bash
git add src/zotero_arxiv_daily/executor.py src/zotero_arxiv_daily/corpus/
git commit -m "refactor: executor uses ZoteroLoader, remove duplicate logic"
```
