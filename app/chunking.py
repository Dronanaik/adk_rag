import re


def normalize_text(text: str) -> str:
    """
    Normalize whitespace while preserving double-newline paragraph boundaries
    for structure-aware semantic chunking.
    """
    raw_paragraphs = re.split(r"\n\s*\n", text)
    cleaned_paragraphs = []

    for para in raw_paragraphs:
        lines = []
        for line in para.splitlines():
            cleaned_line = " ".join(line.split())
            if cleaned_line:
                lines.append(cleaned_line)
        if lines:
            cleaned_paragraphs.append("\n".join(lines))

    return "\n\n".join(cleaned_paragraphs)


def _split_markdown_table_block(block: str, chunk_size: int) -> list[str]:
    """
    Split a large Markdown table along row boundaries while preserving the
    table header and separator rows on every continuation chunk so column
    context is never lost.
    """
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    if len(lines) <= 2:
        return [block]

    header_prefix = ""
    data_start = 0
    if lines[0].startswith("|") and len(lines) >= 2 and "---" in lines[1]:
        header_candidate = f"{lines[0]}\n{lines[1]}"
        if len(header_candidate) < chunk_size // 2:
            header_prefix = header_candidate
            data_start = 2

    chunks: list[str] = []
    current_lines: list[str] = [header_prefix] if header_prefix else []

    for row in lines[data_start:]:
        candidate = "\n".join(current_lines + [row]) if current_lines else row
        if len(candidate) <= chunk_size:
            current_lines.append(row)
        else:
            if current_lines and (not header_prefix or len(current_lines) > 1):
                chunks.append("\n".join(current_lines))
            current_lines = [header_prefix, row] if header_prefix else [row]
            if len("\n".join(current_lines)) > chunk_size:
                chunks.append("\n".join(current_lines)[:chunk_size])
                current_lines = [header_prefix] if header_prefix else []

    if current_lines and (not header_prefix or len(current_lines) > 1):
        chunks.append("\n".join(current_lines))

    return chunks or [block[:chunk_size]]


def _split_long_block(block: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Split a single oversized paragraph or Markdown table along row/sentence
    boundaries when possible, falling back to character windows with overlap.
    """
    block_lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    if len(block_lines) >= 3 and sum(1 for ln in block_lines if ln.startswith("|")) >= 2:
        return _split_markdown_table_block(block, chunk_size=chunk_size)

    sentences = re.split(r"(?<=[.!?])\s+", block)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if not sentence:
            continue
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
                overlap_tail = current[-overlap:].strip() if overlap > 0 else ""
                current = f"{overlap_tail} {sentence}".strip() if overlap_tail else sentence
            else:
                current = sentence

            # If a single sentence still exceeds chunk_size, slice with character overlap
            while len(current) > chunk_size:
                chunks.append(current[:chunk_size].strip())
                next_start = max(1, chunk_size - overlap)
                current = current[next_start:].strip()

    if current:
        chunks.append(current)

    return chunks


def chunk_text(
    text: str,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> list[str]:
    """
    Semantic structure-aware chunker inspired by agentic-rag-knowledge-graph.
    Groups paragraphs and headings up to `chunk_size` characters and carries
    overlapping context across chunk boundaries.
    """
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    normalized = normalize_text(text)
    if not normalized:
        return []

    paragraphs = normalized.split("\n\n")
    chunks: list[str] = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(para) > chunk_size:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            sub_chunks = _split_long_block(para, chunk_size=chunk_size, overlap=overlap)
            chunks.extend(sub_chunks)
            continue

        candidate = f"{current_chunk}\n\n{para}" if current_chunk else para
        if len(candidate) <= chunk_size:
            current_chunk = candidate
        else:
            if current_chunk:
                chunks.append(current_chunk)
                overlap_tail = current_chunk[-overlap:].strip() if overlap > 0 else ""
                current_chunk = f"{overlap_tail}\n\n{para}".strip() if overlap_tail else para
                if len(current_chunk) > chunk_size:
                    chunks.append(para)
                    current_chunk = ""
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks
