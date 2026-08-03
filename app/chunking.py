def normalize_text(text: str) -> str:
    lines = []

    for line in text.splitlines():
        cleaned_line = " ".join(line.split())

        if cleaned_line:
            lines.append(cleaned_line)

    return "\n".join(lines)

def chunk_text(
    text: str,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> list[str]:
    """
    Split text into overlapping chunks.

    chunk_size and overlap are measured in characters.
    """

    if overlap >= chunk_size:
        raise ValueError(
            "overlap must be smaller than chunk_size"
        )

    text = normalize_text(text)

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        next_start = end - overlap

        if next_start <= start:
            break

        start = next_start

    return chunks