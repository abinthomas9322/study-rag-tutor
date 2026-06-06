"""Shared test fixtures.

``make_pdf`` builds genuine, valid one-or-more-page PDFs with a real text
layer that pypdf can extract. These are real PDFs (a legitimate test utility),
not fabricated product data.
"""

import io
from collections.abc import Callable

import pytest


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_pdf(pages: list[str]) -> bytes:
    font_num = 3
    page_nums = [4 + 2 * i for i in range(len(pages))]
    content_nums = [5 + 2 * i for i in range(len(pages))]

    objects: dict[int, bytes] = {}
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = b" ".join(b"%d 0 R" % p for p in page_nums)
    objects[2] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, len(pages))
    objects[font_num] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    for i, text in enumerate(pages):
        stream = f"BT /F1 18 Tf 72 200 Td ({_escape(text)}) Tj ET".encode()
        objects[content_nums[i]] = b"<< /Length %d >>\nstream\n%s\nendstream" % (
            len(stream),
            stream,
        )
        objects[page_nums[i]] = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
            b"/Contents %d 0 R /Resources << /Font << /F1 %d 0 R >> >> >>"
            % (content_nums[i], font_num)
        )

    max_num = max(objects)
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for num in range(1, max_num + 1):
        if num in objects:
            offsets[num] = out.tell()
            out.write(b"%d 0 obj\n%s\nendobj\n" % (num, objects[num]))
    xref = out.tell()
    out.write(b"xref\n0 %d\n" % (max_num + 1))
    out.write(b"0000000000 65535 f \n")
    for num in range(1, max_num + 1):
        if num in offsets:
            out.write(b"%010d 00000 n \n" % offsets[num])
        else:
            out.write(b"0000000000 00000 f \n")
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (max_num + 1, xref))
    return out.getvalue()


@pytest.fixture
def make_pdf() -> Callable[..., bytes]:
    """Return a factory: ``make_pdf("page one", "page two") -> bytes``."""

    def _make(*pages: str) -> bytes:
        return _build_pdf(list(pages) if pages else [""])

    return _make
