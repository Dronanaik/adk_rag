"""Document file validation, magic-byte inspection, PDF/Markdown parsing, and chunking."""

from pathlib import Path

import pymupdf

from app.schemas.common import APIException
from app.schemas.documents import AllowedMimeType
from app.utils.chunker import TextChunkSpan, chunk_document_text

PDF_MAGIC_HEADER = b"%PDF-"


def sanitize_filename(filename: str) -> str:
    """Strip path traversal components and validate that filename is non-empty (AGENTS.md 8.3)."""
    cleaned = filename.replace("\\", "/").strip()
    if not cleaned:
        raise APIException(
            status_code=400,
            code="VALIDATION_ERROR",
            message="Invalid or empty filename.",
            details={"filename": filename},
        )
    basename = Path(cleaned).name.strip()
    if not basename or basename in (".", "..") or basename.startswith("."):
        raise APIException(
            status_code=400,
            code="VALIDATION_ERROR",
            message="Invalid or empty filename.",
            details={"filename": filename},
        )
    return basename


def derive_document_title(
    filename: str,
    raw_bytes: bytes | None = None,
    mime_type: AllowedMimeType | None = None,
) -> str:
    """Derive a clean human-readable document title from Markdown H1 or sanitized filename."""
    if raw_bytes and mime_type == "text/markdown":
        try:
            text = raw_bytes.decode("utf-8")
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("# "):
                    heading = stripped[2:].strip()
                    if heading:
                        return heading[:200]
        except UnicodeDecodeError:
            pass

    stem = Path(filename).stem.strip()
    if not stem:
        return filename
    normalized = stem.replace("_", " ").replace("-", " ")
    return " ".join(normalized.split()) or filename


def detect_and_validate_mime_type(
    filename: str,
    raw_bytes: bytes,
    declared_content_type: str | None = None,
    max_upload_size_mb: int = 20,
) -> AllowedMimeType:
    """Validate file size, extension, and magic bytes/UTF-8 encoding (API.md 5.2)."""
    _ = declared_content_type
    max_size_bytes = max_upload_size_mb * 1024 * 1024
    if len(raw_bytes) == 0:
        raise APIException(
            status_code=400,
            code="VALIDATION_ERROR",
            message="Uploaded file cannot be empty.",
            details={"filename": filename},
        )
    if len(raw_bytes) > max_size_bytes:
        raise APIException(
            status_code=413,
            code="FILE_TOO_LARGE",
            message=f"Uploaded file exceeds the maximum allowed size of {max_upload_size_mb} MB.",
            details={"filename": filename, "file_size_bytes": len(raw_bytes)},
        )

    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        if not raw_bytes.startswith(PDF_MAGIC_HEADER):
            raise APIException(
                status_code=415,
                code="UNSUPPORTED_MEDIA_TYPE",
                message="Invalid PDF file: missing '%PDF-' magic header.",
                details={"filename": filename},
            )
        return "application/pdf"

    if suffix in (".md", ".markdown", ".txt"):
        if b"\x00" in raw_bytes:
            raise APIException(
                status_code=415,
                code="UNSUPPORTED_MEDIA_TYPE",
                message="Binary null bytes detected in text/markdown upload.",
                details={"filename": filename},
            )
        try:
            raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise APIException(
                status_code=415,
                code="UNSUPPORTED_MEDIA_TYPE",
                message="Text or Markdown file must be valid UTF-8 encoded text.",
                details={"filename": filename},
            ) from exc
        return "text/markdown" if suffix in (".md", ".markdown") else "text/plain"

    raise APIException(
        status_code=415,
        code="UNSUPPORTED_MEDIA_TYPE",
        message="Unsupported file format. Only .pdf, .md, and .txt files are supported.",
        details={"filename": filename, "extension": suffix},
    )


def _extract_pdf_chunks(
    raw_bytes: bytes,
    chunk_size: int,
    chunk_overlap: int,
) -> list[TextChunkSpan]:
    """Extract text page-by-page from a PDF and split into deterministic chunks."""
    try:
        doc = pymupdf.open(stream=raw_bytes, filetype="pdf")
    except Exception as exc:
        raise APIException(
            status_code=415,
            code="UNSUPPORTED_MEDIA_TYPE",
            message=f"Failed to parse PDF document: {exc}",
        ) from exc

    all_spans: list[TextChunkSpan] = []
    cumulative_offset = 0
    try:
        for page_idx in range(len(doc)):
            page = doc.load_page(page_idx)
            page_text = str(page.get_text("text") or "")
            page_spans = chunk_document_text(
                page_text,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                page_number=page_idx + 1,
            )
            for span in page_spans:
                all_spans.append(
                    TextChunkSpan(
                        chunk_index=len(all_spans),
                        content=span.content,
                        content_hash=span.content_hash,
                        char_start=cumulative_offset + span.char_start,
                        char_end=cumulative_offset + span.char_end,
                        token_count=span.token_count,
                        section_heading=span.section_heading,
                        page_number=page_idx + 1,
                    )
                )
            cumulative_offset += len(page_text) + 1
    finally:
        doc.close()

    if not all_spans:
        raise APIException(
            status_code=415,
            code="UNSUPPORTED_MEDIA_TYPE",
            message="PDF contains zero extractable text (scanned image without text layer).",
        )
    return all_spans


def parse_and_chunk_document(
    raw_bytes: bytes,
    mime_type: AllowedMimeType,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[TextChunkSpan]:
    """Parse raw file bytes into deterministic TextChunkSpan items with page/offset tracking."""
    if mime_type == "application/pdf":
        return _extract_pdf_chunks(raw_bytes, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    text = raw_bytes.decode("utf-8")
    spans = chunk_document_text(
        text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        page_number=1,
    )
    if not spans:
        raise APIException(
            status_code=400,
            code="VALIDATION_ERROR",
            message="Document contains no extractable text content.",
        )
    return spans
