import json
import uuid
from typing import Any

from psycopg2.extras import RealDictCursor, execute_values

from app.database import get_db_connection, init_postgres_db
from app.embeddings import embed_text, embed_texts

_schema_initialized = False


def _ensure_schema() -> None:
    global _schema_initialized
    if not _schema_initialized:
        init_postgres_db()
        _schema_initialized = True


def add_document_chunks(
    user_id: str,
    document_id: str,
    filename: str,
    chunks: list[str],
    character_count: int = 0,
    entity_count: int = 0,
    relationship_count: int = 0,
    precomputed_embeddings: list[list[float]] | None = None,
) -> int:
    """
    Embed and store document metadata and chunks in Neon PostgreSQL (pgvector).
    """
    if not chunks:
        return 0

    _ensure_schema()
    embeddings = (
        precomputed_embeddings
        if precomputed_embeddings is not None
        else embed_texts(chunks)
    )

    doc_uuid = uuid.UUID(str(document_id))

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (
                    id, user_id, filename, chunk_count,
                    entity_count, relationship_count, character_count
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    chunk_count = EXCLUDED.chunk_count,
                    entity_count = EXCLUDED.entity_count,
                    relationship_count = EXCLUDED.relationship_count,
                    character_count = EXCLUDED.character_count;
                """,
                (
                    str(doc_uuid),
                    user_id,
                    filename,
                    len(chunks),
                    entity_count,
                    relationship_count,
                    character_count,
                ),
            )

            rows = []
            for idx, (chunk_text, vector) in enumerate(zip(chunks, embeddings)):
                chunk_uuid = str(uuid.uuid4())
                metadata = {
                    "user_id": user_id,
                    "document_id": str(doc_uuid),
                    "filename": filename,
                    "chunk_index": idx,
                }
                rows.append(
                    (
                        chunk_uuid,
                        str(doc_uuid),
                        user_id,
                        filename,
                        idx,
                        chunk_text,
                        vector,
                        json.dumps(metadata),
                    )
                )

            execute_values(
                cur,
                """
                INSERT INTO document_chunks (
                    id, document_id, user_id, filename,
                    chunk_index, content, embedding, metadata
                ) VALUES %s
                """,
                rows,
                template="(%s::uuid, %s::uuid, %s, %s, %s, %s, %s::vector, %s::jsonb)",
            )

    return len(chunks)


def update_document_graph_counts(
    user_id: str,
    document_id: str,
    entity_count: int,
    relationship_count: int,
) -> None:
    """
    Update extracted entity and relationship counts for a document after Neo4j ingestion.
    """
    _ensure_schema()
    with get_db_connection(register_pgvector=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE documents
                SET entity_count = %s,
                    relationship_count = %s
                WHERE id = %s::uuid AND user_id = %s;
                """,
                (entity_count, relationship_count, str(document_id), user_id),
            )


def delete_document_chunks(
    user_id: str,
    document_id: str,
) -> int:
    """
    Delete a document and all its chunks (via ON DELETE CASCADE) from Neon PostgreSQL.
    Returns the number of deleted chunks.
    """
    _ensure_schema()
    with get_db_connection(register_pgvector=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM document_chunks
                WHERE document_id = %s::uuid AND user_id = %s;
                """,
                (str(document_id), user_id),
            )
            row = cur.fetchone()
            chunk_count = int(row[0]) if row else 0

            cur.execute(
                """
                DELETE FROM documents
                WHERE id = %s::uuid AND user_id = %s;
                """,
                (str(document_id), user_id),
            )
            deleted_docs = cur.rowcount

            if deleted_docs == 0 and chunk_count > 0:
                cur.execute(
                    """
                    DELETE FROM document_chunks
                    WHERE document_id = %s::uuid AND user_id = %s;
                    """,
                    (str(document_id), user_id),
                )

    return chunk_count


def search_documents(
    user_id: str,
    query: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Semantic vector similarity search using pgvector cosine distance (<=>).
    Strictly scoped to the authenticated user_id.
    """
    _ensure_schema()
    query_embedding = embed_text(query)

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    document_id::text AS document_id,
                    filename,
                    chunk_index,
                    content AS text,
                    (embedding <=> %s::vector) AS distance,
                    1.0 - (embedding <=> %s::vector) AS similarity
                FROM document_chunks
                WHERE user_id = %s
                ORDER BY embedding <=> %s::vector ASC
                LIMIT %s;
                """,
                (
                    query_embedding,
                    query_embedding,
                    user_id,
                    query_embedding,
                    top_k,
                ),
            )
            records = cur.fetchall()

    matches = []
    for row in records:
        matches.append(
            {
                "text": row["text"],
                "distance": round(float(row["distance"]), 4),
                "similarity": round(float(row["similarity"]), 4),
                "metadata": {
                    "user_id": user_id,
                    "document_id": row["document_id"],
                    "filename": row["filename"],
                    "chunk_index": row["chunk_index"],
                },
            }
        )

    return matches


def hybrid_search_documents(
    user_id: str,
    query: str,
    top_k: int = 5,
    text_weight: float = 0.3,
) -> list[dict[str, Any]]:
    """
    Hybrid search combining pgvector semantic cosine similarity and PostgreSQL
    Full-Text Search (ts_rank_cd + websearch_to_tsquery), inspired by
    coleam00/ottomator-agents/agentic-rag-knowledge-graph.
    """
    _ensure_schema()
    query_embedding = embed_text(query)
    vector_weight = 1.0 - text_weight

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                WITH scored AS (
                    SELECT
                        document_id::text AS document_id,
                        filename,
                        chunk_index,
                        content AS text,
                        (embedding <=> %s::vector) AS distance,
                        (1.0 - (embedding <=> %s::vector)) AS vector_similarity,
                        COALESCE(
                            ts_rank_cd(
                                to_tsvector('english', content),
                                websearch_to_tsquery('english', %s)
                            ),
                            0.0
                        ) AS keyword_score
                    FROM document_chunks
                    WHERE user_id = %s
                )
                SELECT
                    document_id,
                    filename,
                    chunk_index,
                    text,
                    distance,
                    vector_similarity,
                    keyword_score,
                    (vector_similarity * %s + LEAST(keyword_score, 1.0) * %s) AS combined_score
                FROM scored
                ORDER BY combined_score DESC
                LIMIT %s;
                """,
                (
                    query_embedding,
                    query_embedding,
                    query,
                    user_id,
                    vector_weight,
                    text_weight,
                    top_k,
                ),
            )
            records = cur.fetchall()

    matches = []
    for row in records:
        matches.append(
            {
                "text": row["text"],
                "distance": round(float(row["distance"]), 4),
                "vector_similarity": round(float(row["vector_similarity"]), 4),
                "keyword_score": round(float(row["keyword_score"]), 4),
                "combined_score": round(float(row["combined_score"]), 4),
                "metadata": {
                    "user_id": user_id,
                    "document_id": row["document_id"],
                    "filename": row["filename"],
                    "chunk_index": row["chunk_index"],
                },
            }
        )

    return matches


def list_user_documents(user_id: str) -> list[dict[str, Any]]:
    """
    List all documents uploaded by a user from Neon PostgreSQL.
    """
    _ensure_schema()
    with get_db_connection(register_pgvector=False) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    id::text AS document_id,
                    filename,
                    chunk_count AS chunks,
                    entity_count AS entities,
                    relationship_count AS relationships,
                    character_count AS characters,
                    created_at
                FROM documents
                WHERE user_id = %s
                ORDER BY created_at DESC;
                """,
                (user_id,),
            )
            rows = cur.fetchall()

    documents = []
    for row in rows:
        documents.append(
            {
                "document_id": row["document_id"],
                "filename": row["filename"],
                "chunks": int(row["chunks"] or 0),
                "entities": int(row["entities"] or 0),
                "relationships": int(row["relationships"] or 0),
                "characters": int(row["characters"] or 0),
                "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
            }
        )

    return documents


def get_vector_store_stats() -> dict[str, Any]:
    """
    Return aggregate chunk and document counts from Neon PostgreSQL.
    """
    _ensure_schema()
    with get_db_connection(register_pgvector=False) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM document_chunks;")
            total_chunks = int(cur.fetchone()[0])
            cur.execute("SELECT COUNT(*) FROM documents;")
            total_documents = int(cur.fetchone()[0])

    return {
        "total_chunks": total_chunks,
        "total_documents": total_documents,
    }
