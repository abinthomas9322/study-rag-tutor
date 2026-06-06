"""Extract plain text from PDF files using pypdf."""

from typing import IO

from pypdf import PdfReader


def extract_text(source: str | IO[bytes]) -> str:
    """Extract text from every page of a PDF, joined by newlines.

    Args:
        source: A filesystem path or a binary file-like object (e.g. an
            uploaded file's stream).

    Returns:
        The concatenated page text. May be empty for image-only/scanned PDFs
        that contain no extractable text layer.
    """
    reader = PdfReader(source)
    return "\n".join((page.extract_text() or "") for page in reader.pages)
