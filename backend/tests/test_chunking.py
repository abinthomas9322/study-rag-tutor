"""Unit tests for the text chunker, parametrised across the input space."""

import pytest

from rag.chunking import chunk_text


# --- Empty / whitespace input ---------------------------------------------
@pytest.mark.parametrize("text", ["", "   ", "\n\n", "\t  \n"])
def test_empty_or_whitespace_yields_no_chunks(text: str) -> None:
    assert chunk_text(text) == []


# --- Short input (smaller than one chunk) ---------------------------------
def test_text_shorter_than_size_is_single_chunk() -> None:
    assert chunk_text("hello world", size=800, overlap=120) == ["hello world"]


# --- Whitespace normalisation ---------------------------------------------
def test_whitespace_is_collapsed() -> None:
    assert chunk_text("a\n\n  b\t c", size=800) == ["a b c"]


# --- Chunk sizing ----------------------------------------------------------
def test_no_chunk_exceeds_size() -> None:
    text = "x" * 5000
    chunks = chunk_text(text, size=800, overlap=120)
    assert all(len(c) <= 800 for c in chunks)
    assert len(chunks) > 1


def test_consecutive_chunks_overlap_by_exactly_overlap() -> None:
    text = "".join(str(i % 10) for i in range(2000))
    size, overlap = 500, 100
    chunks = chunk_text(text, size=size, overlap=overlap)
    # The tail of one chunk equals the head of the next by `overlap` chars.
    for a, b in zip(chunks, chunks[1:], strict=False):
        assert a[-overlap:] == b[:overlap]


def test_full_text_is_covered_with_no_gaps() -> None:
    text = "".join(str(i % 10) for i in range(3333))
    size, overlap = 400, 80
    chunks = chunk_text(text, size=size, overlap=overlap)
    # Reconstruct by dropping the overlapping prefix of every chunk after the
    # first; the result must equal the normalised source exactly.
    rebuilt = chunks[0] + "".join(c[overlap:] for c in chunks[1:])
    assert rebuilt == text


@pytest.mark.parametrize("overlap", [0, 1, 200, 399])
def test_valid_overlaps_accepted(overlap: int) -> None:
    chunks = chunk_text("y" * 1000, size=400, overlap=overlap)
    assert chunks  # non-empty


# --- Invalid arguments -----------------------------------------------------
@pytest.mark.parametrize("size", [0, -1, -800])
def test_non_positive_size_raises(size: int) -> None:
    with pytest.raises(ValueError, match="size must be positive"):
        chunk_text("some text", size=size)


@pytest.mark.parametrize("overlap", [-1, 400, 401, 1000])
def test_overlap_out_of_range_raises(overlap: int) -> None:
    with pytest.raises(ValueError, match=r"\[0, size\)"):
        chunk_text("some text", size=400, overlap=overlap)
