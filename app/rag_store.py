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
    content_hash: str = "",
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
    doc_metadata = {"content_hash": content_hash} if content_hash else {}

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (
                    id, user_id, filename, chunk_count,
                    entity_count, relationship_count, character_count, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (id) DO UPDATE SET
                    chunk_count = EXCLUDED.chunk_count,
                    entity_count = EXCLUDED.entity_count,
                    relationship_count = EXCLUDED.relationship_count,
                    character_count = EXCLUDED.character_count,
                    metadata = EXCLUDED.metadata;
                """,
                (
                    str(doc_uuid),
                    user_id,
                    filename,
                    len(chunks),
                    entity_count,
                    relationship_count,
                    character_count,
                    json.dumps(doc_metadata),
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


def delete_all_user_documents(user_id: str) -> dict[str, int]:
    """
    Delete all documents and chunks belonging to user_id from Neon PostgreSQL.
    Returns counts of deleted documents and chunks.
    """
    _ensure_schema()
    with get_db_connection(register_pgvector=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM document_chunks
                WHERE user_id = %s;
                """,
                (user_id,),
            )
            row = cur.fetchone()
            chunk_count = int(row[0]) if row else 0

            cur.execute(
                """
                DELETE FROM documents
                WHERE user_id = %s;
                """,
                (user_id,),
            )
            deleted_docs = cur.rowcount

            cur.execute(
                """
                DELETE FROM document_chunks
                WHERE user_id = %s;
                """,
                (user_id,),
            )

    return {
        "deleted_documents": deleted_docs,
        "deleted_chunks": chunk_count,
    }


def find_existing_user_document(
    user_id: str,
    filename: str,
    content_hash: str,
    character_count: int = 0,
    first_chunk_text: str = "",
) -> dict[str, Any]:
    """
    Inspect existing documents for the user to detect redundant or updated uploads:
      - exact_match: same filename + same content_hash
      - content_match: different filename + same content_hash
      - filename_matches: same filename + different content_hash (older versions to replace)
    Also backfills metadata.content_hash for legacy documents when character_count and
    the first chunk match.
    """
    _ensure_schema()
    exact_match: dict[str, Any] | None = None
    content_match: dict[str, Any] | None = None
    filename_matches: list[dict[str, Any]] = []

    with get_db_connection(register_pgvector=False) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    d.id::text AS document_id,
                    d.filename,
                    d.chunk_count AS chunks,
                    d.entity_count AS entities,
                    d.relationship_count AS relationships,
                    d.character_count AS characters,
                    d.metadata->>'content_hash' AS content_hash,
                    dc.content AS first_chunk_content
                FROM documents d
                LEFT JOIN document_chunks dc
                    ON dc.document_id = d.id AND dc.chunk_index = 0
                WHERE d.user_id = %s
                ORDER BY d.created_at DESC;
                """,
                (user_id,),
            )
            rows = cur.fetchall()

            for row in rows:
                row_hash = (row.get("content_hash") or "").strip()
                is_same_content = False

                if row_hash and content_hash:
                    is_same_content = row_hash == content_hash
                elif (
                    not row_hash
                    and content_hash
                    and character_count > 0
                    and int(row.get("characters") or 0) == character_count
                    and (row.get("first_chunk_content") or "").strip() == first_chunk_text.strip()
                ):
                    is_same_content = True
                    cur.execute(
                        """
                        UPDATE documents
                        SET metadata = jsonb_set(
                            COALESCE(metadata, '{}'::jsonb),
                            '{content_hash}',
                            to_jsonb(%s::text)
                        )
                        WHERE id = %s::uuid AND user_id = %s;
                        """,
                        (content_hash, row["document_id"], user_id),
                    )

                doc_info = {
                    "document_id": row["document_id"],
                    "filename": row["filename"],
                    "chunks": int(row.get("chunks") or 0),
                    "entities": int(row.get("entities") or 0),
                    "relationships": int(row.get("relationships") or 0),
                    "characters": int(row.get("characters") or 0),
                    "content_hash": content_hash if is_same_content else row_hash,
                }

                if row["filename"] == filename and is_same_content:
                    if exact_match is None:
                        exact_match = doc_info
                    else:
                        filename_matches.append(doc_info)
                elif row["filename"] != filename and is_same_content:
                    if content_match is None:
                        content_match = doc_info
                elif row["filename"] == filename and not is_same_content:
                    filename_matches.append(doc_info)

    return {
        "exact_match": exact_match,
        "content_match": content_match,
        "filename_matches": filename_matches,
    }


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


def get_document_preview(user_id: str, document_id: str) -> dict[str, Any] | None:
    """
    Fetch document metadata and ordered indexed chunks for previewing an uploaded document.
    Returns None if the document ID is invalid or does not belong to user_id.
    """
    try:
        parsed_id = str(uuid.UUID(str(document_id)))
    except (ValueError, TypeError):
        return None

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
                WHERE id = %s::uuid AND user_id = %s;
                """,
                (parsed_id, user_id),
            )
            doc_row = cur.fetchone()
            if not doc_row:
                return None

            cur.execute(
                """
                SELECT
                    chunk_index,
                    content,
                    metadata
                FROM document_chunks
                WHERE document_id = %s::uuid AND user_id = %s
                ORDER BY chunk_index ASC;
                """,
                (parsed_id, user_id),
            )
            chunk_rows = cur.fetchall()

    chunks = [
        {
            "chunk_index": int(row["chunk_index"]),
            "content": row["content"] or "",
            "char_count": len(row["content"] or ""),
        }
        for row in chunk_rows
    ]
    full_text = "\n\n".join(c["content"] for c in chunks if c["content"])

    return {
        "document_id": doc_row["document_id"],
        "filename": doc_row["filename"],
        "chunks": int(doc_row["chunks"] or len(chunks)),
        "entities": int(doc_row["entities"] or 0),
        "relationships": int(doc_row["relationships"] or 0),
        "characters": int(doc_row["characters"] or len(full_text)),
        "created_at": doc_row["created_at"].isoformat() if doc_row.get("created_at") else None,
        "full_text": full_text,
        "chunk_list": chunks,
    }


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
