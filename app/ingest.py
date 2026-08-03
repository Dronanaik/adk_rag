import os
import uuid

from app.chunking import chunk_text
from app.parsers import extract_text
from app.rag_store import add_document_chunks

def ingest_document(
    file_path: str,
    filename: str,
    user_id: str,
) -> dict:
    """
    Extract, chunk, embed, and store one document.
    """

    document_id = str(uuid.uuid4())

    text = extract_text(file_path)

    if not text.strip():
        raise ValueError(
            "No readable text was found in the document."
        )

    chunks = chunk_text(
        text,
        chunk_size=1200,
        overlap=200,
    )

    number_of_chunks = add_document_chunks(
        user_id=user_id,
        document_id=document_id,
        filename=filename,
        chunks=chunks,
    )

    return {
        "document_id": document_id,
        "filename": filename,
        "chunks_created": number_of_chunks,
        "characters_extracted": len(text),
    }