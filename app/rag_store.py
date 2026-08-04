import uuid
from typing import Any

from app.database import index as pc_index
from app.embeddings import embed_text, embed_texts

def add_document_chunks(
    user_id: str,
    document_id: str,
    filename: str,
    chunks: list[str],
) -> int:
    """
    Embed and store document chunks in Pinecone.
    """

    if not chunks:
        return 0

    embeddings = embed_texts(chunks)

    vectors = []
    for i, chunk in enumerate(chunks):
        # Format: user_id#document_id#index#uuid
        chunk_id = f"{user_id}#{document_id}#{i}#{uuid.uuid4().hex[:8]}"
        
        vectors.append({
            "id": chunk_id,
            "values": embeddings[i],
            "metadata": {
                "user_id": user_id,
                "document_id": document_id,
                "filename": filename,
                "chunk_index": i,
                "text": chunk
            }
        })

    pc_index.upsert(vectors=vectors)

    return len(chunks)


def delete_document_chunks(
    user_id: str,
    document_id: str,
) -> int:
    """
    Delete all Pinecone chunks belonging to a document and user.
    """
    
    # Pinecone Serverless supports deleting by filter
    # Alternatively we can list IDs with prefix and delete
    chunk_ids = []
    for ids in pc_index.list(prefix=f"{user_id}#{document_id}#"):
        chunk_ids.extend([i if isinstance(i, str) else getattr(i, 'id', str(i)) for i in ids])
        
    if not chunk_ids:
        return 0
        
    # Delete in batches of 1000
    for i in range(0, len(chunk_ids), 1000):
        batch = chunk_ids[i:i+1000]
        pc_index.delete(ids=batch)

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

    result = pc_index.query(
        vector=query_embedding,
        top_k=top_k,
        filter={
            "user_id": user_id,
        },
        include_metadata=True,
    )

    matches = []

    for match in result.get("matches", []):
        metadata = match.get("metadata", {})
        text = metadata.pop("text", "")
        matches.append(
            {
                "text": text,
                "metadata": metadata,
                # convert similarity score to a distance metric to be compatible
                "distance": 1.0 - match.get("score", 1.0),
            }
        )

    return matches


def list_user_documents(user_id: str) -> list[dict[str, Any]]:
    """
    List all documents for a user using Pinecone prefix listing.
    """
    documents = {}
    doc_first_chunk_ids = []

    for ids in pc_index.list(prefix=f"{user_id}#"):
        for chunk_item in ids:
            chunk_id = chunk_item if isinstance(chunk_item, str) else getattr(chunk_item, 'id', str(chunk_item))
            parts = chunk_id.split("#")
            if len(parts) >= 3:
                doc_id = parts[1]
                if doc_id not in documents:
                    documents[doc_id] = {
                        "document_id": doc_id,
                        "filename": f"Unknown ({doc_id})",
                        "chunks": 0,
                    }
                    doc_first_chunk_ids.append(chunk_id)
                documents[doc_id]["chunks"] += 1

    if doc_first_chunk_ids:
        # Fetch metadata in batches of 1000
        for i in range(0, len(doc_first_chunk_ids), 1000):
            batch = doc_first_chunk_ids[i:i+1000]
            fetch_res = pc_index.fetch(ids=batch)
            for chunk_id, record in fetch_res.get("vectors", {}).items():
                metadata = record.get("metadata", {})
                doc_id = metadata.get("document_id")
                filename = metadata.get("filename")
                if doc_id and doc_id in documents and filename:
                    documents[doc_id]["filename"] = filename

    return list(documents.values())