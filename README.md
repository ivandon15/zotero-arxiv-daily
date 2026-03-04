<p align="center">
  <a href="" rel="noopener">
 <img width=200px height=200px src="assets/logo.svg" alt="logo"></a>
</p>

<h3 align="center">Zotero-arXiv-Daily</h3>

<div align="center">

  [![Status](https://img.shields.io/badge/status-active-success.svg)]()
  ![Stars](https://img.shields.io/github/stars/TideDra/zotero-arxiv-daily?style=flat)
  [![GitHub Issues](https://img.shields.io/github/issues/TideDra/zotero-arxiv-daily)](https://github.com/TideDra/zotero-arxiv-daily/issues)
  [![GitHub Pull Requests](https://img.shields.io/github/issues-pr/TideDra/zotero-arxiv-daily)](https://github.com/TideDra/zotero-arxiv-daily/pulls)
  [![License](https://img.shields.io/github/license/TideDra/zotero-arxiv-daily)](/LICENSE)
  [<img src="https://api.gitsponsors.com/api/badge/img?id=893025857" height="20">](https://api.gitsponsors.com/api/badge/link?p=PKMtRut1dWWuC1oFdJweyDSvJg454/GkdIx4IinvBblaX2AY4rQ7FYKAK1ZjApoiNhYEeduIEhfeZVIwoIVlvcwdJXVFD2nV2EE5j6lYXaT/RHrcsQbFl3aKe1F3hliP26OMayXOoZVDidl05wj+yg==)

</div>

---

<p align="center"> Recommend new papers of your interest daily from arXiv, Nature, Science, and any RSS feed — via email or MCP.
    <br>
</p>

> [!IMPORTANT]
> Please keep an eye on this repo, and merge your forked repo in time when there is any update of this upstream, in order to enjoy new features and fix found bugs.

## 🧐 About <a name = "about"></a>

> Track new scientific researches of your interest by just forking (and staring) this repo!😊

*Zotero-arXiv-Daily* finds arxiv papers that may attract you based on the context of your Zotero library, and then sends the result to your mailbox📮. It can be deployed as Github Action Workflow with **zero cost**, **no installation**, and **few configuration** of Github Action environment variables for daily **automatic** delivery.

## ✨ Features
- Totally free! All the calculation can be done in the Github Action runner locally within its quota (for public repo).
- AI-generated TL;DR for you to quickly pick up target papers.
- Affiliations of the paper are resolved and presented.
- Links to papers sorted by relevance with your recent research interest.
- Fast deployment via fork this repo and set environment variables in the Github Action Page.
- Support LLM API for generating TL;DR of papers.
- Ignore unwanted Zotero papers using glob pattern.
- **Universal RSS retriever** — fetch from any RSS/Atom feed source:
  - arXiv (any category): `"arxiv:cs.AI"`, `"arxiv:cs.LG+cs.CV"`, etc.
  - BioRxiv / MedRxiv: `"biorxiv:neuroscience"`, `"medrxiv:psychiatry"`
  - Nature, Science, Cell, PNAS, PLOS, eLife, PubMed
  - Any custom RSS/Atom URL
- **MCP server** — expose the full pipeline as tools for AI agents.

## 📷 Screenshot
![screenshot](./assets/screenshot.png)

## 🚀 Usage
### Quick Start
1. Fork (and star😘) this repo.
![fork](./assets/fork.png)

2. Set Github Action environment variables.
![secrets](./assets/secrets.png)

Below are all the secrets you need to set. They are invisible to anyone including you once they are set, for security.

| Key |Description | Example |
| :---  | :---  | :--- |
| ZOTERO_ID  | User ID of your Zotero account. **User ID is not your username, but a sequence of numbers**Get your ID from [here](https://www.zotero.org/settings/security). You can find it at the position shown in this [screenshot](https://github.com/TideDra/zotero-arxiv-daily/blob/main/assets/userid.png). | 12345678  |
| ZOTERO_KEY | An Zotero API key with read access. Get a key from [here](https://www.zotero.org/settings/security).  | AB5tZ877P2j7Sm2Mragq041H   |
| SENDER | The email account of the SMTP server that sends you email. | abc@qq.com |
| SENDER_PASSWORD | The password of the sender account. Note that it's not necessarily the password for logging in the e-mail client, but the authentication code for SMTP service. Ask your email provider for this.   | abcdefghijklmn |
| RECEIVER | The e-mail address that receives the paper list. | abc@outlook.com |
| OPENAI_API_KEY | API Key when using the API to access LLMs. You can get FREE API for using advanced open source LLMs in [SiliconFlow](https://cloud.siliconflow.cn/i/b3XhBRAm). | sk-xxx |
| OPENAI_API_BASE | API URL when using the API to access LLMs. | https://api.siliconflow.cn/v1 |

Then you should also set a public variable `CUSTOM_CONFIG` for your custom configuration.
![vars](./assets/repo_var.png)
![custom_config](./assets/config_var.png)
Paste the following content into the value of `CUSTOM_CONFIG` variable:
```yaml
zotero:
  user_id: ${oc.env:ZOTERO_ID}
  api_key: ${oc.env:ZOTERO_KEY}
  include_path: null

email:
  sender: ${oc.env:SENDER}
  receiver: ${oc.env:RECEIVER}
  smtp_server: smtp.qq.com
  smtp_port: 465
  sender_password: ${oc.env:SENDER_PASSWORD}

llm:
  api:
    key: ${oc.env:OPENAI_API_KEY}
    base_url: ${oc.env:OPENAI_API_BASE}
  generation_kwargs:
    model: gpt-4o-mini

source:
  rss:
    feeds: ["arxiv:cs.AI", "arxiv:cs.CV", "arxiv:cs.LG", "arxiv:cs.CL"]
    since_days: 1

executor:
  debug: ${oc.env:DEBUG,null}
  source: ['rss']
```
>[!NOTE]
> `${oc.env:XXX,yyy}` means the value of the environment variable `XXX`. If the variable is not set, the default value `yyy` will be used.

Here is the full configuration, `???` means the value must be filled in:
```yaml
zotero:
  user_id: ??? # User ID of your Zotero account.
  api_key: ??? # A Zotero API key with read access.
  include_path: null # A glob pattern to filter Zotero collections. Example: "2026/survey/**"

source:
  rss:
    feeds: []  # List of feed specs. Examples:
               #   "arxiv:cs.AI"          — arXiv CS.AI category
               #   "arxiv:cs.AI+cs.LG"    — multiple arXiv categories combined
               #   "biorxiv:neuroscience" — BioRxiv neuroscience
               #   "medrxiv:psychiatry"   — MedRxiv psychiatry
               #   "nature"               — Nature journal
               #   "science"              — Science journal
               #   "cell"                 — Cell journal
               #   "pnas"                 — PNAS
               #   "plos_biology"         — PLOS Biology
               #   "elife"                — eLife
               #   "pubmed_trending"      — PubMed trending
               #   "https://..."          — any custom RSS/Atom URL
    since_days: 1  # Only retrieve papers from the last N days. Set to null for all available.

email:
  sender: ??? # The email account of the SMTP server that sends you email. Example: abc@qq.com
  receiver: ??? # The email account that receives the paper list. Example: abc@outlook.com
  smtp_server: ??? # The SMTP server. Ask your email provider. Example: smtp.qq.com
  smtp_port: ??? # The port of SMTP server. Example: 465
  sender_password: ??? # The SMTP authentication code (not your login password). Example: abcdefghijklmn

llm:
  api:
    key: ??? # API Key of your LLM API. Example: sk-xxx
    base_url: ??? # API URL of your LLM API. Example: https://api.openai.com/v1
  generation_kwargs:
    max_tokens: 16384
    model: ???
  language: English # Preferred language for the TL;DR. Example: English

reranker:
  local:
    model: jinaai/jina-embeddings-v5-text-nano
    encode_kwargs:
      task: retrieval
      prompt_name: document
  api:
    key: null
    base_url: null
    model: null

executor:
  debug: false
  send_empty: false
  max_workers: 10
  max_paper_num: 100
  source: [rss]
  reranker: local # 'local' or 'api'
```

That's all! Now you can test the workflow by manually triggering it:
![test](./assets/test.png)

> [!NOTE]
> The Test-Workflow Action is the debug version of the main workflow (Send-emails-daily), which always retrieve 5 arxiv papers regardless of the date. While the main workflow will be automatically triggered everyday and retrieve new papers released yesterday. There is no new arxiv paper at weekends and holiday, in which case you may see "No new papers found" in the log of main workflow.

Then check the log and the receiver email after it finishes.

By default, the main workflow runs on 22:00 UTC everyday. You can change this time by editting the workflow config `.github/workflows/main.yml`.

### Local Running
Supported by [uv](https://github.com/astral-sh/uv), this workflow can easily run on your local device if uv is installed:
```bash
# set all the environment variables
# export ZOTERO_ID=xxxx
# ...
cd zotero-arxiv-daily
uv run src/zotero_arxiv_daily/main.py
```

### MCP Server

The pipeline is also exposed as an MCP server for use with AI agents (Claude, Cursor, etc.).

**Start the server:**
```bash
uv run zotero-arxiv-mcp
```

**Configure in Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "zotero-arxiv-daily": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/zotero-arxiv-daily", "zotero-arxiv-mcp"]
    }
  }
}
```

**Available MCP tools:**

| Tool | Description |
| :--- | :--- |
| `list_sources` | List all available named feed sources |
| `register_feed_source` | Register a custom RSS/Atom feed by name |
| `fetch_corpus` | Load interest corpus from Zotero or a local PDF folder |
| `retrieve_papers` | Fetch latest papers from RSS feeds |
| `rerank_papers` | Rank candidate papers against your corpus |
| `generate_tldr` | Generate a one-sentence TL;DR for a paper |
| `run_pipeline` | Run the full pipeline end-to-end |

**Example agent workflow:**
```
1. fetch_corpus({"type": "zotero", "user_id": "...", "api_key": "..."})
   — or —
   fetch_corpus({"type": "pdf_dir", "path": "/my/papers"})

2. retrieve_papers(feeds=["arxiv:cs.AI", "nature"], since_days=1)

3. rerank_papers(papers, corpus)

4. generate_tldr(paper, llm_config)
```

The agent can also pass a natural language description as a corpus by constructing a fake corpus entry:
```python
corpus = [{"title": "interests", "abstract": "I work on transformer optimization and low-resource NLP", "added_date": "...", "paths": []}]
rerank_papers(papers, corpus)
```

## 🚀 Sync with the latest version
This project is in active development. You can subscribe this repo via `Watch` so that you can be notified once we publish new release.

![Watch](./assets/subscribe_release.png)


## 📖 How it works
*Zotero-arXiv-Daily* fetches papers from RSS/Atom feeds (arXiv, Nature, Science, BioRxiv, or any custom feed), then ranks them against your interest corpus (Zotero library or local PDFs) using embedding similarity. Newer papers in your corpus get higher weight. The TL;DR of each paper is generated by an LLM using the abstract. Results are delivered by email or returned via MCP tools.

## 📌 Limitations
- The recommendation algorithm is very simple, it may not accurately reflect your interest. Welcome better ideas for improving the algorithm!
- High `MAX_PAPER_NUM` can lead the execution time exceed the limitation of Github Action runner (6h per execution for public repo, and 2000 mins per month for private repo). Commonly, the quota given to public repo is definitely enough for individual use. If you have special requirements, you can deploy the workflow in your own server, or use a self-hosted Github Action runner, or pay for the exceeded execution time.

## 👯‍♂️ Contribution
Any issue and PR are welcomed! But remember that **each PR should merge to the `dev` branch**.

## 📃 License
Distributed under the AGPLv3 License. See `LICENSE` for detail.

## ❤️ Acknowledgement
- [pyzotero](https://github.com/urschrei/pyzotero)
- [feedparser](https://github.com/kurtmckee/feedparser)
- [sentence_transformers](https://github.com/UKPLab/sentence-transformers)
- [paperlib](https://github.com/Future-Scholars/paperlib) — inspiration for RSS source handling

## ☕ Buy Me A Coffee
If you find this project helpful, welcome to sponsor me via WeChat or via [ko-fi](https://ko-fi.com/tidedra).
![wechat_qr](assets/wechat_sponsor.JPG)


## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=TideDra/zotero-arxiv-daily&type=Date)](https://star-history.com/#TideDra/zotero-arxiv-daily&Date)
