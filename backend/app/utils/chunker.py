"""Deterministic text and Markdown chunking utility with character offsets."""

from dataclasses import dataclass

from app.utils.hashing import compute_sha256_text


@dataclass(frozen=True, slots=True)
class TextChunkSpan:
    """Immutable chunk slice with character offsets and content hash."""

    chunk_index: int
    content: str
    content_hash: str
    char_start: int
    char_end: int
    token_count: int
    section_heading: str | None = None
    page_number: int | None = None


def estimate_token_count(text: str) -> int:
    """Estimate token count deterministically (~4 characters per token, minimum 1)."""
    stripped = text.strip()
    if not stripped:
        return 0
    return max(1, (len(stripped) + 3) // 4)


def _find_break_offset(text: str, start: int, target_end: int) -> int:
    """Find a clean paragraph, line, or sentence boundary near target_end."""
    if target_end >= len(text):
        return len(text)
    search_floor = start + max(1, (target_end - start) // 2)
    for separator in ("\n\n", "\n", ". ", " "):
        idx = text.rfind(separator, search_floor, target_end)
        if idx != -1:
            return idx + len(separator)
    return target_end


def chunk_document_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    page_number: int | None = None,
) -> list[TextChunkSpan]:
    """Split text into overlapping, boundary-aware chunks with exact character spans."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and < chunk_size")

    normalized = text.replace("\r\n", "\n")
    if not normalized.strip():
        return []

    spans: list[TextChunkSpan] = []
    cursor = 0
    length = len(normalized)
    current_heading: str | None = None

    while cursor < length:
        while cursor < length and normalized[cursor].isspace():
            cursor += 1
        if cursor >= length:
            break

        raw_end = min(length, cursor + chunk_size)
        end = _find_break_offset(normalized, cursor, raw_end)
        if end <= cursor:
            end = raw_end

        slice_text = normalized[cursor:end].strip()
        for line in slice_text.splitlines():
            if line.startswith("#"):
                current_heading = line.lstrip("#").strip() or current_heading

        if slice_text:
            spans.append(
                TextChunkSpan(
                    chunk_index=len(spans),
                    content=slice_text,
                    content_hash=compute_sha256_text(slice_text),
                    char_start=cursor,
                    char_end=end,
                    token_count=estimate_token_count(slice_text),
                    section_heading=current_heading,
                    page_number=page_number,
                )
            )

        if end >= length:
            break
        next_cursor = end - chunk_overlap
        cursor = next_cursor if next_cursor > cursor else end

    return spans

