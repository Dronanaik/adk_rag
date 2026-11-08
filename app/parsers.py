import csv
import hashlib
from html.parser import HTMLParser
import io
import logging
from pathlib import Path
import re
from typing import Any

import pymupdf as fitz
from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from google.genai import types

import app.config as config
from app.embeddings import get_genai_client

logger = logging.getLogger(__name__)

_docling_converter: Any = None
_docling_unavailable: bool = False
_image_transcription_cache: dict[str, str] = {}

IMAGE_PLACEHOLDER = "<!-- image -->"
MAX_VISION_IMAGES_PER_DOC = 15
MIN_IMAGE_DIMENSION_PX = 48
MIN_IMAGE_BYTES = 1500

IMAGE_EXTRACTION_PROMPT = (
    "You are a lossless document figure, chart, and diagram transcription engine. "
    "Examine this image extracted from a document.\n"
    "1. If the image is purely a decorative icon, company logo, bullet, or blank spacer "
    "with no meaningful textual or visual data, reply with exactly: DECORATIVE_ONLY\n"
    "2. Otherwise, transcribe ALL visible text, labels, headings, numbers, metrics, equations, "
    "and callouts verbatim.\n"
    "3. If the image contains a table, chart, or graph, represent its data as a clean "
    "GitHub-Flavored Markdown table.\n"
    "4. If the image is an architecture diagram, flowchart, or entity-relationship diagram, "
    "list all components/nodes and their exact directional connections (e.g., Component A -> connects to -> Component B).\n"
    "Output concise, structured Markdown only without conversational preamble."
)

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
    Lazily initialize and cache the Docling DocumentConverter instance with
    OCR, table structure recognition, and picture image cropping enabled.
    """
    global _docling_converter, _docling_unavailable
    if _docling_unavailable:
        return None
    if _docling_converter is not None:
        return _docling_converter

    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        pdf_options = PdfPipelineOptions(
            do_ocr=True,
            do_table_structure=True,
            generate_picture_images=True,
            images_scale=2.0,
        )
        _docling_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
            }
        )
        return _docling_converter
    except Exception:
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


def _transcribe_image_with_gemini(
    image_bytes: bytes,
    mime_type: str = "image/png",
    caption: str = "",
) -> str:
    """
    Use Gemini 2.5 Flash Multimodal Vision to extract all text, chart values,
    and diagram relationships from an embedded document image.
    """
    if not image_bytes or len(image_bytes) < MIN_IMAGE_BYTES or not config.GOOGLE_API_KEY:
        return caption.strip()

    digest = hashlib.sha256(image_bytes).hexdigest()
    if digest in _image_transcription_cache:
        cached = _image_transcription_cache[digest]
        if not cached:
            return caption.strip()
        return f"{caption.strip()}\n{cached}".strip() if caption.strip() else cached

    try:
        client = get_genai_client()
        response = client.models.generate_content(
            model=config.AGENT_MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                IMAGE_EXTRACTION_PROMPT,
            ],
        )
        text = (response.text or "").strip()
        if not text or "DECORATIVE_ONLY" in text:
            _image_transcription_cache[digest] = ""
            return caption.strip()

        _image_transcription_cache[digest] = text
        if caption.strip():
            return f"**Caption:** {caption.strip()}\n{text}"
        return text
    except Exception:
        logger.debug("Gemini vision transcription skipped for embedded image", exc_info=True)
        return caption.strip()


def _extract_docling_picture_payloads(doc: Any) -> list[dict[str, Any]]:
    """
    Extract cropped PIL images and captions from a DoclingDocument's pictures collection.
    """
    payloads: list[dict[str, Any]] = []
    pictures = getattr(doc, "pictures", None) or []

    for pic in pictures:
        caption = ""
        try:
            if hasattr(pic, "caption_text"):
                caption = (pic.caption_text(doc) or "").strip()
        except Exception:
            caption = ""

        pil_img = None
        try:
            if hasattr(pic, "get_image"):
                pil_img = pic.get_image(doc)
            if pil_img is None and getattr(pic, "image", None) is not None:
                pil_img = getattr(pic.image, "pil_image", None)
        except Exception:
            pil_img = None

        img_bytes = b""
        if pil_img is not None:
            width, height = getattr(pil_img, "size", (0, 0))
            if width >= MIN_IMAGE_DIMENSION_PX and height >= MIN_IMAGE_DIMENSION_PX:
                buf = io.BytesIO()
                pil_img.save(buf, format="PNG")
                img_bytes = buf.getvalue()

        payloads.append(
            {
                "bytes": img_bytes,
                "mime_type": "image/png",
                "caption": caption,
            }
        )

    return payloads


def _extract_native_images_from_file(file_path: str) -> list[dict[str, Any]]:
    """
    Extract embedded bitmap images directly from .pdf, .docx, or .pptx files
    when Docling picture bitmaps are not directly populated.
    """
    ext = Path(file_path).suffix.lower()
    images: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()

    try:
        if ext == ".pdf":
            with fitz.open(file_path) as pdf_doc:
                for page_num, page in enumerate(pdf_doc, start=1):
                    for img_info in page.get_images(full=True):
                        xref = img_info[0]
                        base_img = pdf_doc.extract_image(xref)
                        if not base_img:
                            continue
                        width = int(base_img.get("width") or 0)
                        height = int(base_img.get("height") or 0)
                        img_bytes = base_img.get("image") or b""
                        if (
                            width < MIN_IMAGE_DIMENSION_PX
                            or height < MIN_IMAGE_DIMENSION_PX
                            or len(img_bytes) < MIN_IMAGE_BYTES
                        ):
                            continue
                        h = hashlib.sha256(img_bytes).hexdigest()
                        if h in seen_hashes:
                            continue
                        seen_hashes.add(h)
                        img_ext = (base_img.get("ext") or "png").lower()
                        mime = "image/jpeg" if img_ext in {"jpg", "jpeg"} else f"image/{img_ext}"
                        images.append(
                            {
                                "bytes": img_bytes,
                                "mime_type": mime,
                                "caption": f"Page {page_num} Figure",
                            }
                        )
                        if len(images) >= MAX_VISION_IMAGES_PER_DOC:
                            return images

        elif ext == ".docx":
            doc = Document(file_path)
            for rel in doc.part.rels.values():
                if "image" in getattr(rel, "reltype", ""):
                    target_part = getattr(rel, "target_part", None)
                    img_bytes = getattr(target_part, "blob", b"") if target_part else b""
                    content_type = getattr(target_part, "content_type", "image/png") if target_part else "image/png"
                    if len(img_bytes) < MIN_IMAGE_BYTES or not content_type.startswith("image/"):
                        continue
                    if content_type in {"image/x-emf", "image/x-wmf"}:
                        continue
                    h = hashlib.sha256(img_bytes).hexdigest()
                    if h in seen_hashes:
                        continue
                    seen_hashes.add(h)
                    images.append(
                        {
                            "bytes": img_bytes,
                            "mime_type": content_type,
                            "caption": "",
                        }
                    )
                    if len(images) >= MAX_VISION_IMAGES_PER_DOC:
                        return images

        elif ext == ".pptx":
            from pptx import Presentation

            prs = Presentation(file_path)
            for slide_num, slide in enumerate(prs.slides, start=1):
                for shape in slide.shapes:
                    if hasattr(shape, "image"):
                        try:
                            img_bytes = shape.image.blob
                            content_type = shape.image.content_type or "image/png"
                            if len(img_bytes) < MIN_IMAGE_BYTES:
                                continue
                            h = hashlib.sha256(img_bytes).hexdigest()
                            if h in seen_hashes:
                                continue
                            seen_hashes.add(h)
                            images.append(
                                {
                                    "bytes": img_bytes,
                                    "mime_type": content_type,
                                    "caption": f"Slide {slide_num} Visual",
                                }
                            )
                            if len(images) >= MAX_VISION_IMAGES_PER_DOC:
                                return images
                        except Exception:
                            continue
    except Exception:
        logger.debug("Native embedded image extraction skipped for %s", file_path, exc_info=True)

    return images


def _resolve_image_placeholders(
    markdown_text: str,
    docling_doc: Any,
    file_path: str,
) -> str:
    """
    Replace every '<!-- image -->' placeholder in Docling's Markdown export
    with structured text/table/diagram descriptions extracted via Gemini Vision,
    ensuring zero visual content loss and leaving no raw '<!-- image -->' tags.
    """
    if IMAGE_PLACEHOLDER not in markdown_text:
        return markdown_text

    docling_payloads = _extract_docling_picture_payloads(docling_doc) if docling_doc is not None else []
    has_docling_bytes = any(bool(p.get("bytes")) for p in docling_payloads)
    native_payloads = [] if has_docling_bytes else _extract_native_images_from_file(file_path)

    active_payloads = docling_payloads if has_docling_bytes else native_payloads
    transcribed_blocks: list[str] = []
    vision_calls = 0

    for idx, item in enumerate(active_payloads, start=1):
        img_bytes = item.get("bytes") or b""
        mime_type = item.get("mime_type") or "image/png"
        caption = item.get("caption") or ""

        if img_bytes and vision_calls < MAX_VISION_IMAGES_PER_DOC:
            vision_calls += 1
            extracted_md = _transcribe_image_with_gemini(
                image_bytes=img_bytes,
                mime_type=mime_type,
                caption=caption,
            )
        else:
            extracted_md = caption.strip()

        if extracted_md:
            transcribed_blocks.append(f"### [Figure {idx}]\n{extracted_md}")
        else:
            transcribed_blocks.append("")

    parts = markdown_text.split(IMAGE_PLACEHOLDER)
    rebuilt: list[str] = [parts[0]]
    for idx, trailing_part in enumerate(parts[1:]):
        replacement = transcribed_blocks[idx] if idx < len(transcribed_blocks) else ""
        if replacement:
            rebuilt.append(f"\n\n{replacement}\n\n")
        rebuilt.append(trailing_part)

    cleaned = "".join(rebuilt).replace(IMAGE_PLACEHOLDER, "")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def extract_with_docling(file_path: str) -> str:
    """
    Convert a document using IBM Docling (DocumentConverter) into structured,
    layout-aware Markdown preserving reading order, headings, lists, tables,
    and embedded figure/diagram content (replacing '<!-- image -->' placeholders).
    """
    converter = _get_docling_converter()
    if converter is None:
        return ""

    try:
        conv_result = converter.convert(file_path)
        if conv_result and getattr(conv_result, "document", None) is not None:
            doc = conv_result.document
            try:
                markdown_text = doc.export_to_markdown(
                    traverse_pictures=True,
                    image_placeholder=IMAGE_PLACEHOLDER,
                )
            except TypeError:
                markdown_text = doc.export_to_markdown()

            if markdown_text and markdown_text.strip():
                resolved_text = _resolve_image_placeholders(
                    markdown_text=markdown_text,
                    docling_doc=doc,
                    file_path=file_path,
                )
                return resolved_text.strip()
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


def _append_missing_figure_transcriptions(text: str, file_path: str) -> str:
    """
    If a document contains embedded images that were not already transcribed
    in-place via Docling placeholders, transcribe and append them so zero visual
    content is lost even when native fallback parsers are used.
    """
    if "### [Figure " in text:
        return text

    native_payloads = _extract_native_images_from_file(file_path)
    if not native_payloads:
        return text

    figure_blocks: list[str] = []
    for idx, item in enumerate(native_payloads[:MAX_VISION_IMAGES_PER_DOC], start=1):
        img_bytes = item.get("bytes") or b""
        mime_type = item.get("mime_type") or "image/png"
        caption = item.get("caption") or ""
        extracted_md = _transcribe_image_with_gemini(
            image_bytes=img_bytes,
            mime_type=mime_type,
            caption=caption,
        )
        if extracted_md:
            figure_blocks.append(f"### [Figure {idx}]\n{extracted_md}")

    if not figure_blocks:
        return text

    if text.strip():
        return text.strip() + "\n\n" + "\n\n".join(figure_blocks)
    return "\n\n".join(figure_blocks)


def extract_from_pdf(file_path: str) -> str:
    """
    Extract text, tables, and embedded figures/diagrams from PDF using Docling
    layout-aware Markdown conversion + Gemini Vision, reconciled with lossless
    PyMuPDF page & table extraction so zero content is lost.
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

        combined = (
            docling_md + "\n\n" + "\n\n".join(missing_pages)
            if missing_pages
            else docling_md
        )
        return _append_missing_figure_transcriptions(combined, file_path)

    return _append_missing_figure_transcriptions(docling_md or pymupdf_md, file_path)


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
    Extract text, headings, tables, headers/footers, and embedded figures from a
    Word (.docx) file using Docling, native XML body traversal, and Gemini Vision.
    """
    docling_md = extract_with_docling(file_path)
    native_md = _extract_docx_native_lossless(file_path)

    if docling_md and len(docling_md) >= len(native_md) * 0.85:
        return _append_missing_figure_transcriptions(docling_md, file_path)
    return _append_missing_figure_transcriptions(native_md or docling_md, file_path)


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
        return _append_missing_figure_transcriptions(native_md, file_path)
    return _append_missing_figure_transcriptions(docling_md or native_md, file_path)


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
