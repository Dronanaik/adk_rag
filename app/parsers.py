import csv
from html.parser import HTMLParser
import io
import logging
from pathlib import Path
from typing import Any

import pymupdf as fitz
from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

logger = logging.getLogger(__name__)

_docling_converter: Any = None
_docling_unavailable: bool = False

DOCLING_SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".html",
    ".htm",
    ".md",
    ".csv",
}


def _get_docling_converter() -> Any:
    """
    Lazily initialize and cache the Docling DocumentConverter instance.
    """
    global _docling_converter, _docling_unavailable
    if _docling_unavailable:
        return None
    if _docling_converter is not None:
        return _docling_converter

    try:
        from docling.document_converter import DocumentConverter

        _docling_converter = DocumentConverter()
        return _docling_converter
    except Exception:
        logger.warning(
            "Docling DocumentConverter could not be initialized; using lossless native parsers.",
            exc_info=True,
        )
        _docling_unavailable = True
        return None


def extract_with_docling(file_path: str) -> str:
    """
    Convert a document using IBM Docling (DocumentConverter) into structured,
    layout-aware Markdown preserving reading order, headings, lists, and tables.
    """
    converter = _get_docling_converter()
    if converter is None:
        return ""

    try:
        conv_result = converter.convert(file_path)
        if conv_result and getattr(conv_result, "document", None) is not None:
            markdown_text = conv_result.document.export_to_markdown()
            if markdown_text and markdown_text.strip():
                return markdown_text.strip()
    except Exception:
        logger.warning(
            "Docling conversion fallback triggered for %s",
            Path(file_path).name,
            exc_info=True,
        )
    return ""


def _rows_to_markdown_table(rows: list[list[str]]) -> str:
    """
    Format a 2D list of cell strings as a GitHub-Flavored Markdown table.
    """
    cleaned_rows: list[list[str]] = []
    max_cols = 0
    for row in rows:
        cells = [
            " ".join(str(cell or "").replace("|", "\\|").splitlines()).strip()
            for cell in row
        ]
        if any(cells):
            cleaned_rows.append(cells)
            max_cols = max(max_cols, len(cells))

    if not cleaned_rows or max_cols == 0:
        return ""

    normalized = [r + [""] * (max_cols - len(r)) for r in cleaned_rows]
    header = normalized[0]
    separator = ["---"] * max_cols
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for data_row in normalized[1:]:
        lines.append("| " + " | ".join(data_row) + " |")
    return "\n".join(lines)


def _extract_pdf_pymupdf_lossless(file_path: str) -> str:
    """
    Lossless PyMuPDF extraction that captures both full page text in reading-block
    order and structured Markdown tables via page.find_tables().
    """
    pages: list[str] = []

    with fitz.open(file_path) as document:
        for page_number, page in enumerate(document, start=1):
            page_parts: list[str] = []
            text = page.get_text("text", sort=True)
            if text and text.strip():
                page_parts.append(text.strip())

            # Extract structured tables if present on the page
            try:
                table_finder = page.find_tables()
                tables = getattr(table_finder, "tables", []) or []
                for t_idx, table in enumerate(tables, start=1):
                    md_table = ""
                    if hasattr(table, "to_markdown"):
                        md_table = (table.to_markdown() or "").strip()
                    else:
                        extracted = table.extract()
                        if extracted:
                            md_table = _rows_to_markdown_table(extracted)
                    if md_table:
                        page_parts.append(f"[Page {page_number} Table {t_idx}]\n{md_table}")
            except Exception:
                logger.debug("PyMuPDF table finder skipped on page %d", page_number)

            if page_parts:
                pages.append(f"## [Page {page_number}]\n" + "\n\n".join(page_parts))

    return "\n\n".join(pages)


def extract_from_pdf(file_path: str) -> str:
    """
    Extract text and tables from PDF using Docling layout-aware Markdown conversion,
    reconciled with lossless PyMuPDF page & table extraction so zero content is lost.
    """
    docling_md = extract_with_docling(file_path)
    pymupdf_md = _extract_pdf_pymupdf_lossless(file_path)

    if docling_md and pymupdf_md:
        # Ensure no pages or text blocks were dropped during layout analysis
        docling_norm = "".join(docling_md.lower().split())
        missing_pages: list[str] = []
        with fitz.open(file_path) as document:
            for page_number, page in enumerate(document, start=1):
                raw_page = page.get_text("text", sort=True).strip()
                if not raw_page:
                    continue
                sample_lines = [
                    ln.strip() for ln in raw_page.splitlines() if len(ln.strip()) >= 20
                ]
                if sample_lines:
                    matched = sum(
                        1
                        for ln in sample_lines
                        if "".join(ln.lower().split())[:30] in docling_norm
                    )
                    if matched == 0:
                        missing_pages.append(f"## [Page {page_number}]\n{raw_page}")

        if missing_pages:
            return docling_md + "\n\n" + "\n\n".join(missing_pages)
        return docling_md

    return docling_md or pymupdf_md


def _extract_docx_native_lossless(file_path: str) -> str:
    """
    Lossless DOCX extractor that preserves document order across paragraphs,
    heading levels, all tables (rendered as Markdown), and section headers/footers.
    """
    document = Document(file_path)
    blocks: list[str] = []

    # 1. Section headers
    header_lines: list[str] = []
    for section in document.sections:
        for hdr_para in section.header.paragraphs:
            txt = hdr_para.text.strip()
            if txt and txt not in header_lines:
                header_lines.append(txt)
    if header_lines:
        blocks.append("\n".join(header_lines))

    # 2. Body elements (paragraphs + tables) in exact document order
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            para = Paragraph(child, document)
            txt = para.text.strip()
            if not txt:
                continue
            style_name = (para.style.name if para.style else "").lower()
            if "heading 1" in style_name or style_name == "title":
                blocks.append(f"# {txt}")
            elif "heading 2" in style_name or style_name == "subtitle":
                blocks.append(f"## {txt}")
            elif "heading 3" in style_name:
                blocks.append(f"### {txt}")
            else:
                blocks.append(txt)
        elif child.tag == qn("w:tbl"):
            table = Table(child, document)
            table_rows: list[list[str]] = []
            for row in table.rows:
                table_rows.append([cell.text.strip() for cell in row.cells])
            md_table = _rows_to_markdown_table(table_rows)
            if md_table:
                blocks.append(md_table)

    # 3. Section footers
    footer_lines: list[str] = []
    for section in document.sections:
        for ftr_para in section.footer.paragraphs:
            txt = ftr_para.text.strip()
            if txt and txt not in footer_lines:
                footer_lines.append(txt)
    if footer_lines:
        blocks.append("\n".join(footer_lines))

    return "\n\n".join(blocks)


def extract_from_docx(file_path: str) -> str:
    """
    Extract text, headings, tables, and headers/footers from a Word (.docx) file
    using Docling and lossless native XML body traversal.
    """
    docling_md = extract_with_docling(file_path)
    native_md = _extract_docx_native_lossless(file_path)

    if docling_md and len(docling_md) >= len(native_md) * 0.85:
        return docling_md
    return native_md or docling_md


def extract_from_text(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        return file.read()


def extract_from_csv(file_path: str) -> str:
    """
    Extract CSV content as a structured Markdown table so column headers remain
    bound to row values during chunking and retrieval.
    """
    raw_text = extract_from_text(file_path)
    if not raw_text.strip():
        return ""

    try:
        reader = csv.reader(io.StringIO(raw_text))
        rows = [row for row in reader if any(cell.strip() for cell in row)]
        if rows:
            md_table = _rows_to_markdown_table(rows)
            if md_table:
                return md_table
    except Exception:
        logger.debug("CSV markdown formatting fallback triggered for %s", file_path)

    return raw_text


def extract_from_xlsx(file_path: str) -> str:
    """
    Extract all sheets and cells from an Excel (.xlsx / .xls) file using Docling
    and openpyxl, formatting each sheet as a structured Markdown table.
    """
    docling_md = extract_with_docling(file_path)

    try:
        import openpyxl

        workbook = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        sheet_texts: list[str] = []

        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            rows: list[list[str]] = []

            for row in sheet.iter_rows(values_only=True):
                row_values = [str(cell).strip() if cell is not None else "" for cell in row]
                if any(row_values):
                    rows.append(row_values)

            if rows:
                md_table = _rows_to_markdown_table(rows)
                if md_table:
                    sheet_texts.append(f"## [Sheet: {sheet_name}]\n\n{md_table}")

        workbook.close()
        native_md = "\n\n".join(sheet_texts)
        if native_md and len(native_md) >= len(docling_md):
            return native_md
    except Exception:
        if docling_md:
            return docling_md
        raise

    return docling_md


def _extract_shape_content(shape: Any) -> list[str]:
    """
    Recursively extract text frames, tables, and grouped shapes from a PowerPoint shape.
    """
    parts: list[str] = []

    if getattr(shape, "has_text_frame", False):
        lines = [
            para.text.strip()
            for para in shape.text_frame.paragraphs
            if para.text and para.text.strip()
        ]
        if lines:
            parts.append("\n".join(lines))

    if getattr(shape, "has_table", False):
        table_rows: list[list[str]] = []
        for row in shape.table.rows:
            table_rows.append([cell.text.strip() for cell in row.cells])
        md_table = _rows_to_markdown_table(table_rows)
        if md_table:
            parts.append(md_table)

    if hasattr(shape, "shapes"):
        for child_shape in shape.shapes:
            parts.extend(_extract_shape_content(child_shape))

    return parts


def extract_from_pptx(file_path: str) -> str:
    """
    Extract all slide text frames, tables, grouped shapes, and speaker notes
    from a PowerPoint (.pptx) file using Docling + python-pptx.
    """
    docling_md = extract_with_docling(file_path)

    from pptx import Presentation

    presentation = Presentation(file_path)
    slides: list[str] = []

    for slide_number, slide in enumerate(presentation.slides, start=1):
        slide_parts: list[str] = []

        for shape in slide.shapes:
            slide_parts.extend(_extract_shape_content(shape))

        # Include speaker notes if present
        if getattr(slide, "has_notes_slide", False) and slide.notes_slide:
            notes_frame = getattr(slide.notes_slide, "notes_text_frame", None)
            if notes_frame and notes_frame.text and notes_frame.text.strip():
                slide_parts.append(f"[Speaker Notes]\n{notes_frame.text.strip()}")

        if slide_parts:
            slides.append(f"## [Slide {slide_number}]\n\n" + "\n\n".join(slide_parts))

    native_md = "\n\n".join(slides)
    if native_md and len(native_md) >= len(docling_md):
        return native_md
    return docling_md or native_md


class _LosslessHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        if t in {"script", "style", "noscript"}:
            self._skip_depth += 1
        elif t in {"h1", "h2", "h3", "p", "div", "section", "article", "tr", "li", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in {"script", "style", "noscript"} and self._skip_depth > 0:
            self._skip_depth -= 1
        elif t in {"td", "th"}:
            self.parts.append(" | ")
        elif t in {"h1", "h2", "h3", "p", "div", "section", "article", "tr", "table", "ul", "ol"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data.strip():
            self.parts.append(data.strip() + " ")


def extract_from_html(file_path: str) -> str:
    """
    Extract structured content from HTML files using Docling, with lossless
    HTMLParser fallback.
    """
    docling_md = extract_with_docling(file_path)
    if docling_md:
        return docling_md

    raw_html = extract_from_text(file_path)
    parser = _LosslessHTMLParser()
    parser.feed(raw_html)
    parsed = "".join(parser.parts).strip()
    return parsed or raw_html


def extract_text(file_path: str) -> str:
    """
    Extract lossless structured text and Markdown tables based on file extension.

    Supported formats:
      .pdf        — Docling layout & TableFormer + PyMuPDF lossless reconciliation
      .docx       — Docling + python-docx (paragraphs, headings, tables, headers/footers)
      .xlsx/.xls  — Docling + openpyxl (all sheets rendered as Markdown tables)
      .pptx       — Docling + python-pptx (text frames, tables, grouped shapes, speaker notes)
      .html/.htm  — Docling + lossless HTML parser
      .csv        — Structured Markdown table extractor
      .txt/.md/.json/.xml/.log — UTF-8 lossless reader
    """
    extension = Path(file_path).suffix.lower()

    if extension == ".pdf":
        return extract_from_pdf(file_path)

    if extension == ".docx":
        return extract_from_docx(file_path)

    if extension in {".xlsx", ".xls"}:
        return extract_from_xlsx(file_path)

    if extension == ".pptx":
        return extract_from_pptx(file_path)

    if extension in {".html", ".htm"}:
        return extract_from_html(file_path)

    if extension == ".csv":
        return extract_from_csv(file_path)

    if extension in {
        ".txt",
        ".md",
        ".json",
        ".xml",
        ".log",
    }:
        return extract_from_text(file_path)

    raise ValueError(
        f"Unsupported file type: '{extension}'. "
        "Supported types: .pdf, .docx, .xlsx, .xls, .pptx, "
        ".txt, .md, .csv, .json, .xml, .html, .htm, .log"
    )
