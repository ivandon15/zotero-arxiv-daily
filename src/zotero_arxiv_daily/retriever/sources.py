_BUILTIN: dict[str, str] = {
    "arxiv":     "https://rss.arxiv.org/atom/{param}",
    "biorxiv":   "https://connect.biorxiv.org/biorxiv_xml.php?subject={param}",
    "medrxiv":   "https://connect.medrxiv.org/medrxiv_xml.php?subject={param}",
    "nature":         "https://www.nature.com/nature.rss",
    "science":        "https://www.science.org/rss/news_current.xml",
    "cell":           "https://www.cell.com/cell/rss/current",
    "pnas":           "https://www.pnas.org/rss/current.xml",
    "plos_biology":   "https://journals.plos.org/plosbiology/feed/atom",
    "plos_medicine":  "https://journals.plos.org/plosmedicine/feed/atom",
    "elife":          "https://elifesciences.org/rss/recent.xml",
    "pubmed_trending": "https://pubmed.ncbi.nlm.nih.gov/rss/search/trending/?format=rss",
}

_custom: dict[str, str] = {}


def register_source(name: str, url: str) -> None:
    """Register a custom named source."""
    _custom[name] = url


def list_sources() -> dict[str, str]:
    """Return all registered sources (builtin + custom)."""
    return {**_BUILTIN, **_custom}


def resolve_feed_url(spec: str) -> str:
    """Resolve a feed spec to a URL.

    Spec formats:
      "arxiv:cs.AI"          -> parameterized builtin
      "arxiv:cs.AI+cs.LG"   -> multi-category
      "nature"               -> fixed-URL builtin
      "my_journal"           -> custom registered source
      "https://..."          -> raw URL, returned as-is
    """
    if spec.startswith("http://") or spec.startswith("https://"):
        return spec

    all_sources = list_sources()

    if ":" in spec:
        name, param = spec.split(":", 1)
        if name in all_sources:
            template = all_sources[name]
            if "{param}" in template:
                return template.format(param=param)
        raise ValueError(f"Unknown parameterized source: '{name}'. Available: {list(all_sources)}")

    if spec in all_sources:
        url = all_sources[spec]
        if "{param}" in url:
            raise ValueError(f"Source '{spec}' requires a parameter, e.g. '{spec}:cs.AI'")
        return url

    raise ValueError(f"Unknown source: '{spec}'. Available: {list(all_sources)}")
