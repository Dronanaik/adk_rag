import uuid
from typing import Any

from app.database import collection
from app.embeddings import embed_text, embed_texts

def add_document_chunks(
    user_id: str,
    document_id: str,
    filename: str,
    chunks: list[str],
) -> int:
    """
    Embed and store document chunks in ChromaDB.
    """

    if not chunks:
        return 0

    embeddings = embed_texts(chunks)

    ids = []
    metadatas = []

    for index, chunk in enumerate(chunks):
        chunk_id = f"{document_id}_{index}_{uuid.uuid4().hex[:8]}"

        ids.append(chunk_id)

        metadatas.append(
            {
                "user_id": user_id,
                "document_id": document_id,
                "filename": filename,
                "chunk_index": index,
            }
        )

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return len(chunks)

def search_documents(
    user_id: str,
    query: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Search only documents belonging to the specified user.
    """

    query_embedding = embed_text(query)

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={
            "user_id": user_id,
        },
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    matches = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances,
    ):
        matches.append(
            {
                "text": document,
                "metadata": metadata,
                "distance": distance,
            }
        )

    return matches