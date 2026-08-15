from __future__ import annotations

import re

_WORD_SPLIT = re.compile(r"\s+")


def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 150) -> list[str]:
    """Split text into overlapping, word-boundary chunks.

    Each chunk stays near ``chunk_size`` characters and the next chunk begins
    ``chunk_overlap`` characters back so concepts split across a boundary
    remain retrievable.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if not (0 <= chunk_overlap < chunk_size):
        raise ValueError("chunk_overlap must be between 0 and chunk_size")

    text = text.strip()
    if not text:
        return []

    words = _WORD_SPLIT.split(text)
    n = len(words)
    step = max(1, chunk_size - chunk_overlap)
    chunks: list[str] = []
    start = 0

    while start < n:
        end = start
        length = 0
        while end < n:
            wlen = len(words[end]) + (1 if length else 0)
            if length + wlen > chunk_size and length > 0:
                break
            length += wlen
            end += 1
        if end == start:  # single token longer than chunk_size
            end = start + 1
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)

        start_char = sum(len(w) + 1 for w in words[:start])
        target = start_char + step
        new_start = start
        acc = start_char
        while new_start < n and acc < target:
            acc += len(words[new_start]) + 1
            new_start += 1
        start = new_start if new_start > start else start + 1

    return chunks
