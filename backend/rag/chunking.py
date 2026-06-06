"""Split document text into overlapping chunks for embedding and retrieval.

Overlap keeps context from being cut off at chunk boundaries, so a passage
that straddles two chunks is still retrievable as a whole.
"""


def chunk_text(text: str, *, size: int = 800, overlap: int = 120) -> list[str]:
    """Split ``text`` into overlapping fixed-size character chunks.

    Whitespace is normalised first (runs of spaces/newlines collapse to one
    space) so chunk sizes reflect real content, not formatting.

    Args:
        text: The raw document text.
        size: Maximum characters per chunk. Must be positive.
        overlap: Characters shared between consecutive chunks. Must be in
            ``[0, size)`` — an overlap equal to or larger than ``size`` would
            stop the window from advancing.

    Returns:
        A list of non-empty chunks in document order. Empty or
        whitespace-only input yields an empty list.

    Raises:
        ValueError: If ``size <= 0`` or ``overlap`` is outside ``[0, size)``.
    """
    if size <= 0:
        raise ValueError("size must be positive")
    if not 0 <= overlap < size:
        raise ValueError("overlap must be in the range [0, size)")

    normalised = " ".join(text.split())
    if not normalised:
        return []

    step = size - overlap
    chunks: list[str] = []
    for start in range(0, len(normalised), step):
        chunk = normalised[start : start + size]
        chunks.append(chunk)
        if start + size >= len(normalised):
            break
    return chunks
