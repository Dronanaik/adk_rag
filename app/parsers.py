from pathlib import Path

import fitz
from docx import Document

def extract_from_pdf(file_path: str) -> str:
    document = fitz.open(file_path)

    pages = []

    for page_number, page in enumerate(document, start=1):
        text = page.get_text()

        if text.strip():
            pages.append(
                f"[Page {page_number}]\n{text}"
            )

    return "\n\n".join(pages)

def extract_from_docx(file_path: str) -> str:
    document = Document(file_path)

    paragraphs = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            paragraphs.append(paragraph.text)

    return "\n".join(paragraphs)

def extract_from_text(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        return file.read()

def extract_from_csv(file_path: str) -> str:
    return extract_from_text(file_path)

def extract_text(file_path: str) -> str:
    """
    Extract text based on file extension.
    """

    extension = Path(file_path).suffix.lower()

    if extension == ".pdf":
        return extract_from_pdf(file_path)

    if extension == ".docx":
        return extract_from_docx(file_path)

    if extension in {
        ".txt",
        ".md",
        ".csv",
        ".json",
        ".xml",
        ".html",
        ".htm",
        ".log",
    }:
        return extract_from_text(file_path)

    raise ValueError(
        f"Unsupported file type: {extension}"
    )