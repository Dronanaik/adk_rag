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


def delete_document_chunks(
    user_id: str,
    document_id: str,
) -> int:
    """
    Delete all ChromaDB chunks belonging to a document and user.
    Returns the number of deleted chunks.
    """

    records = collection.get(
        where={
            "$and": [
                {"user_id": user_id},
                {"document_id": document_id},
            ]
        },
        include=[],
    )

    chunk_ids = records.get("ids", [])

    if not chunk_ids:
        return 0

    collection.delete(ids=chunk_ids)

    return len(chunk_ids)



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


def list_user_documents(user_id: str) -> list[dict[str, Any]]:
    records = collection.get(
        where={"user_id": user_id},
        include=["metadatas"],
    )

    documents = {}

    ids = records.get("ids", [])
    metadatas = records.get("metadatas", [])

    for chunk_id, metadata in zip(ids, metadatas):
        metadata = metadata or {}

        document_id = metadata.get("document_id")
        filename = metadata.get("filename")
        chunk_index = metadata.get("chunk_index", 0)

        if not document_id:
            continue

        if document_id not in documents:
            documents[document_id] = {
                "document_id": document_id,
                "filename": filename,
                "chunks": 0,
                "chunk_ids": [],
            }

        documents[document_id]["chunks"] += 1
        documents[document_id]["chunk_ids"].append(chunk_id)

        # Optional: use the smallest chunk index to identify ordering
        documents[document_id]["first_chunk_index"] = min(
            documents[document_id].get("first_chunk_index", chunk_index),
            chunk_index,
        )

    for document in documents.values():
        document.pop("chunk_ids", None)
        document.pop("first_chunk_index", None)

    return list(documents.values())