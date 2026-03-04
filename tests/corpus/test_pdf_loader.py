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
