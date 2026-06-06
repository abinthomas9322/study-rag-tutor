"""Tests for PDF text extraction against real generated PDFs."""

import io
from collections.abc import Callable
from pathlib import Path

from rag.pdf import extract_text


def test_extracts_text_from_single_page(make_pdf: Callable[..., bytes]) -> None:
    data = make_pdf("Mitochondria are the powerhouse of the cell")
    assert "Mitochondria are the powerhouse of the cell" in extract_text(io.BytesIO(data))


def test_concatenates_multiple_pages(make_pdf: Callable[..., bytes]) -> None:
    data = make_pdf("First page about cells", "Second page about energy")
    text = extract_text(io.BytesIO(data))
    assert "First page about cells" in text
    assert "Second page about energy" in text


def test_accepts_a_filesystem_path(make_pdf: Callable[..., bytes], tmp_path: Path) -> None:
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(make_pdf("Hello from disk"))
    assert "Hello from disk" in extract_text(str(pdf_path))


def test_page_without_text_yields_empty(make_pdf: Callable[..., bytes]) -> None:
    text = extract_text(io.BytesIO(make_pdf("")))
    assert text.strip() == ""
