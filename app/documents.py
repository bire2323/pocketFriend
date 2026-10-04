"""PDF text extraction and chunking.

Responsibilities:
  * read PDFs page by page with PyMuPDF
  * split text into retrieval-friendly chunks that keep their page number
  * turn friendly errors into messages a student can act on

No AI is involved here, which makes this module cheap and easy to test.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Optional

from . import config

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class DocumentError(Exception):
    """A user-facing problem with an uploaded PDF."""


# ---------------------------------------------------------------------------
# Data holders
# ---------------------------------------------------------------------------


@dataclass
class PageText:
    """Text from a single PDF page (page numbers are 1-based, like a reader)."""

    page: int
    text: str


@dataclass
class Chunk:
    """A retrievable slice of a document, with provenance."""

    text: str
    filename: str
    page: int
    chunk_id: str

    @property
    def metadata(self) -> dict:
        """Metadata stored in the vector database."""
        return {
            "filename": self.filename,
            "page": int(self.page),
            "chunk_id": self.chunk_id,
        }

    @property
    def source_label(self) -> str:
        return f"{self.filename} — Page {self.page}"


@dataclass
class IngestReport:
    """What happened while ingesting one file. Surfaced to the user."""

    filename: str
    pages: int = 0
    chunks: int = 0
    characters: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        return (
            f"{self.filename}: {self.pages} page(s), {self.chunks} searchable chunk(s)"
        )


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

_LIGATURES = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
}


def normalize_text(text: str) -> str:
    """Clean up extracted text: fix ligatures, unify whitespace, drop page furniture."""
    if not text:
        return ""
    for ligature, replacement in _LIGATURES.items():
        text = text.replace(ligature, replacement)
    text = unicodedata.normalize("NFKC", text)

    # A single "\n" between lines is kept; runs of blank lines collapse.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def _iter_paragraphs(text: str) -> Iterator[str]:
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if block:
            yield block


def chunk_text(
    text: str,
    chunk_size: int = config.CHUNK_SIZE,
    overlap: int = config.CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping chunks, preferring paragraph boundaries.

    Paragraphs are packed together until the chunk size is reached, so a chunk
    usually holds one coherent idea. Very long paragraphs are split on a hard
    character limit with a small overlap so no sentence is lost.
    """
    text = normalize_text(text)
    if not text:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    overlap = max(0, min(overlap, chunk_size - 1))

    chunks: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current.strip():
            chunks.append(current.strip())
        current = ""

    for paragraph in _iter_paragraphs(text):
        # A paragraph longer than the window has to be split on its own.
        if len(paragraph) > chunk_size:
            flush()
            step = max(1, chunk_size - overlap)
            for start in range(0, len(paragraph), step):
                piece = paragraph[start : start + chunk_size].strip()
                if piece:
                    chunks.append(piece)
                if start + chunk_size >= len(paragraph):
                    break
            continue

        if current and len(current) + 1 + len(paragraph) > chunk_size:
            flush()
        current = f"{current}\n\n{paragraph}" if current else paragraph

    flush()
    return chunks


# ---------------------------------------------------------------------------
# PDF reading
# ---------------------------------------------------------------------------


def _page_text(page) -> str:
    """Read one page, keeping paragraph structure where the PDF has it.

    Block extraction separates paragraphs, headings and columns, which makes
    chunks far more useful than one flat stream of lines. Pages that do not
    support blocks fall back to plain text.
    """
    try:
        blocks = page.get_text("blocks")
    except Exception:
        blocks = []

    pieces: list[tuple[float, float, str]] = []
    for block in blocks or []:
        if len(block) < 5:
            continue
        x0, y0, _x1, y1, text = block[0], block[1], block[2], block[3], block[4]
        if block[6] != 0:  # 0 = text, 1 = image
            continue
        text = (text or "").strip()
        if text:
            pieces.append((round(y0, 1), round(x0, 1), text))

    if not pieces:
        return page.get_text("text") or ""

    # Reading order: top to bottom, then left to right.
    pieces.sort(key=lambda item: (item[0], item[1]))
    return "\n\n".join(piece for _y, _x, piece in pieces)


def extract_pages(pdf_source: str | Path | bytes) -> list[PageText]:
    """Extract text page by page from a PDF.

    Accepts a path, raw bytes (what Streamlit uploads give us) or a file-like
    object. Raises DocumentError with an actionable message for anything the
    student can fix (corrupt file, encrypted file, scanned images).
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover - dependency is required
        raise DocumentError(
            "PyMuPDF is not installed. Run: pip install -r requirements.txt"
        ) from exc

    doc = None
    try:
        doc = fitz.open(stream=pdf_source, filetype="pdf") if isinstance(
            pdf_source, bytes
        ) else fitz.open(pdf_source)

        if doc.needs_pass:
            raise DocumentError(
                "This PDF is password protected, so PocketFriend cannot read it. "
                "Please upload an unlocked copy."
            )
        if doc.page_count == 0:
            raise DocumentError("This PDF has no pages. Please check the file.")

        pages: list[PageText] = []
        for index in range(doc.page_count):
            page = doc.load_page(index)
            pages.append(PageText(page=index + 1, text=normalize_text(_page_text(page))))
        return pages
    except DocumentError:
        raise
    except Exception as exc:
        raise DocumentError(
            "PocketFriend couldn't read this PDF. The file may be corrupt or it "
            f"may not really be a PDF.\n\nDetails: {type(exc).__name__}: {exc}"
        ) from exc
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:  # pragma: no cover - closing must never mask errors
                pass


def load_pdf(pdf_source: str | Path | bytes, filename: str = "document.pdf") -> tuple[list[Chunk], IngestReport]:
    """Turn a PDF into chunks that carry filename and page metadata.

    Raises DocumentError when the PDF has no selectable text (a scan).
    """
    pages = extract_pages(pdf_source)
    report = IngestReport(filename=filename, pages=len(pages))
    total_characters = sum(len(page.text) for page in pages)

    if total_characters < 30:
        raise DocumentError(
            "⚠️ PocketFriend couldn't process this PDF.\n\n"
            "The PDF appears to contain scanned images rather than selectable "
            "text, so there is nothing to search. For this version, please "
            "upload a text-based PDF (for example an export from Word, Google "
            "Docs or LaTeX)."
        )

    chunks: list[Chunk] = []
    empty_pages = 0
    for page in pages:
        if not page.text:
            empty_pages += 1
            continue
        for index, piece in enumerate(chunk_text(page.text)):
            chunks.append(
                Chunk(
                    text=piece,
                    filename=filename,
                    page=page.page,
                    chunk_id=build_chunk_id(filename, page.page, index),
                )
            )

    if not chunks:
        raise DocumentError(
            "This PDF has no usable text. Please upload a text-based PDF."
        )
    if empty_pages:
        report.warnings.append(
            f"{empty_pages} page(s) contained no selectable text and were skipped."
        )

    report.chunks = len(chunks)
    report.characters = total_characters
    return chunks, report


def build_chunk_id(filename: str, page: int, index: int) -> str:
    """Stable, readable chunk id: database_notes_4_2 -> page 4, chunk 2."""
    stem = re.sub(r"\.pdf$", "", Path(filename).name, flags=re.IGNORECASE)
    stem = re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_").lower() or "document"
    return f"{stem}_{page}_{index}"


# ---------------------------------------------------------------------------
# Local storage of uploaded files
# ---------------------------------------------------------------------------


def save_upload(data: bytes, filename: str) -> Path:
    """Store an uploaded PDF under data/documents and return its path."""
    config.ensure_directories()
    safe_name = Path(filename).name  # never trust a path from the browser
    if not safe_name.lower().endswith(".pdf"):
        safe_name = f"{safe_name}.pdf"
    target = config.DOCUMENTS_DIR / safe_name
    target.write_bytes(data)
    return target


def stored_documents() -> list[Path]:
    """PDFs already saved in data/documents, newest first."""
    config.ensure_directories()
    files = [p for p in config.DOCUMENTS_DIR.glob("*.pdf") if p.is_file()]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def delete_document(path: str | Path) -> None:
    """Remove a stored PDF from disk (the caller also clears the index)."""
    target = Path(path)
    if target.is_file():
        target.unlink()


def index_uploaded_files() -> Iterable[Path]:
    """Yield every PDF currently stored locally."""
    yield from stored_documents()