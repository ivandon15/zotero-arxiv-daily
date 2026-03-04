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
                    abstract=text[:2000],
                    added_date=mtime,
                    paths=[str(pdf_path.relative_to(self.pdf_dir))],
                ))
            except Exception as e:
                logger.warning(f"Failed to process {pdf_path}: {e}")
        return papers
