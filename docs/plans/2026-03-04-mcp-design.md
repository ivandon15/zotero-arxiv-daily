# MCP Server Design

Date: 2026-03-04

## Goal

Expose the paper fetch + recommendation pipeline as an MCP server so agents can use it directly. The existing GitHub Action / CLI flow remains unchanged.

## New Files

```
src/zotero_arxiv_daily/
  corpus/
    __init__.py
    zotero_loader.py     # extracted from executor.py
    pdf_loader.py        # new: scan a directory of PDFs
  mcp_server.py          # new: MCP entry point
```

## MCP Tools

| Tool | Key Parameters | Returns |
|------|---------------|---------|
| `run_pipeline` | corpus_source, sources, reranker_config, llm_config, send_email=false, email_config? | `list[Paper]` |
| `fetch_corpus` | corpus_source (`{type:"zotero",...}` or `{type:"pdf_dir",path:"..."}`) | `list[CorpusPaper]` |
| `retrieve_papers` | sources, per-source category config | `list[Paper]` |
| `rerank_papers` | papers, corpus, reranker_config | `list[Paper]` sorted by score |
| `generate_tldr` | paper, llm_config | `Paper` with tldr filled |

## PDF Corpus Loader

- Scans all `.pdf` files in a given directory
- Extracts text via existing `extract_markdown_from_pdf`
- Uses filename (without extension) as title
- Uses file `mtime` as `added_date`
- Uses relative path as `paths`

## Configuration

MCP tools accept plain JSON parameters — no hydra dependency. `run_pipeline` has `send_email=false` by default; set to `true` and provide `email_config` to also dispatch via email.

## Constraints

- `Executor` class is not modified
- GitHub Action and CLI entry point (`main.py`) are not modified
- `mcp` package added as a new dependency
