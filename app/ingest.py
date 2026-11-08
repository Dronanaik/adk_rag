import hashlib
import logging
import re
import time
import uuid
from typing import Any

from app.chunking import chunk_text
from app.embeddings import embed_texts
from app.graph_store import add_document_to_graph, delete_document_from_graph
from app.parsers import extract_text
from app.rag_store import (
    add_document_chunks,
    delete_document_chunks,
    find_existing_user_document,
    update_document_graph_counts,
)

logger = logging.getLogger(__name__)

# In-memory live progress state per user_id
_ingestion_progress: dict[str, dict[str, Any]] = {}


def _update_progress(
    user_id: str,
    *,
    state: str,
    current_step: int,
    step_name: str,
    message: str,
    filename: str = "",
    doc_index: int | None = None,
    total_docs: int | None = None,
    step_outputs: dict[str, str] | None = None,
) -> None:
    prev = _ingestion_progress.get(user_id, {})
    merged_outputs = dict(prev.get("step_outputs", {}))
    if step_outputs:
        merged_outputs.update(step_outputs)

    _ingestion_progress[user_id] = {
        "state": state,  # 'running' | 'completed' | 'error' | 'idle'
        "current_step": current_step,  # 1..5
        "step_name": step_name,
        "message": message,
        "filename": filename or prev.get("filename", ""),
        "doc_index": doc_index if doc_index is not None else prev.get("doc_index", 1),
        "total_docs": total_docs if total_docs is not None else prev.get("total_docs", 1),
        "step_outputs": merged_outputs,
        "updated_at": time.time(),
    }


def get_ingestion_progress(user_id: str) -> dict[str, Any]:
    """
    Return the current live ingestion progress for the given user.
    """
    return _ingestion_progress.get(
        user_id,
        {
            "state": "idle",
            "current_step": 0,
            "step_name": "Idle",
            "message": "Ready to ingest documents.",
            "filename": "",
            "doc_index": 1,
            "total_docs": 1,
            "step_outputs": {},
        },
    )


def ingest_document(
    file_path: str,
    filename: str,
    user_id: str,
    doc_index: int = 1,
    total_docs: int = 1,
) -> dict:
    """
    Dual ingestion pipeline with real-time step tracking:
      Step 1: Text extraction from document
      Step 2: Structure-aware semantic chunking
      Step 3: Gemini embedding generation (gemini-embedding-001, 768-dim)
      Step 4: Neon PostgreSQL (pgvector) storage
      Step 5: Neo4j Knowledge Graph entity & relationship extraction
    """
    document_id = str(uuid.uuid4())
    safe_filename = str(filename).replace("\r", "").replace("\n", "")
    _ingestion_progress[user_id] = {
        "step_outputs": {},
        "filename": safe_filename,
        "doc_index": max(1, int(doc_index)),
        "total_docs": max(1, int(total_docs)),
    }

    try:
        # ── Step 1: Lossless Docling & Format-Aware Extraction ──
        _update_progress(
            user_id,
            state="running",
            current_step=1,
            step_name="Lossless Text & Table Extraction (Docling)",
            message=f"Extracting layout-aware Markdown, tables & text from {safe_filename}…",
            filename=safe_filename,
        )
        text = extract_text(file_path)

        if not text.strip():
            raise ValueError("No readable text was found in the document.")

        char_count = len(text)
        _update_progress(
            user_id,
            state="running",
            current_step=2,
            step_name="Structure-Aware Semantic Chunking",
            message=f"Splitting {char_count:,} characters into semantic paragraphs & table-aware chunks…",
            step_outputs={
                "1": f"Losslessly extracted {char_count:,} characters (Markdown + tables) from {safe_filename}"
            },
        )

        # ── Step 2: Semantic Chunking ──
        chunks = chunk_text(
            text,
            chunk_size=1200,
            overlap=200,
        )
        num_chunks = len(chunks)

        # ── Content-Hash Deduplication & Version Check ──
        normalized_text = re.sub(r"\s+", " ", text.strip())
        content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
        existing_check = find_existing_user_document(
            user_id=user_id,
            filename=safe_filename,
            content_hash=content_hash,
            character_count=char_count,
            first_chunk_text=chunks[0] if chunks else "",
        )
        exact_match = existing_check.get("exact_match")
        content_match = existing_check.get("content_match")
        filename_matches = existing_check.get("filename_matches") or []

        # Scenario 1: Exact same file (same filename + same content)
        if exact_match:
            # Clean up any extra duplicate rows if legacy duplicates existed
            for extra_doc in filename_matches:
                extra_id = extra_doc["document_id"]
                delete_document_chunks(user_id=user_id, document_id=extra_id)
                try:
                    delete_document_from_graph(user_id=user_id, document_id=extra_id)
                except Exception:
                    logger.warning("Cleanup warning for extra duplicate %s", extra_id, exc_info=True)

            existing_chunks = int(exact_match.get("chunks") or num_chunks)
            existing_entities = int(exact_match.get("entities") or 0)
            existing_rels = int(exact_match.get("relationships") or 0)
            action_detail = (
                f"Skipped redundant upload — '{safe_filename}' is already indexed with identical content."
            )
            _update_progress(
                user_id,
                state="completed",
                current_step=5,
                step_name="Completed (Already Indexed)",
                message=action_detail,
                step_outputs={
                    "2": f"Verified {num_chunks} semantic chunks (SHA-256: {content_hash[:12]}…)",
                    "3": f"Reused {existing_chunks} × 768-dim Gemini embeddings (unchanged content)",
                    "4": f"Verified existing Neon pgvector record for {safe_filename}",
                    "5": f"Verified {existing_entities} entities & {existing_rels} relationships in Neo4j",
                },
            )
            return {
                "document_id": exact_match["document_id"],
                "filename": safe_filename,
                "chunks_created": existing_chunks,
                "entities_extracted": existing_entities,
                "relationships_extracted": existing_rels,
                "characters_extracted": char_count,
                "ingest_action": "unchanged",
                "content_hash": content_hash[:16],
                "action_detail": action_detail,
            }

        # Scenario 2: Same content uploaded with a different filename
        if content_match:
            existing_fname = content_match["filename"]
            existing_chunks = int(content_match.get("chunks") or num_chunks)
            existing_entities = int(content_match.get("entities") or 0)
            existing_rels = int(content_match.get("relationships") or 0)
            action_detail = (
                f"Skipped duplicate content — '{safe_filename}' has identical content to '{existing_fname}'."
            )
            _update_progress(
                user_id,
                state="completed",
                current_step=5,
                step_name="Completed (Duplicate Content)",
                message=action_detail,
                step_outputs={
                    "2": f"Matched SHA-256 content hash ({content_hash[:12]}…) with {existing_fname}",
                    "3": f"Skipped redundant embedding — reused {existing_chunks} vectors from {existing_fname}",
                    "4": f"Prevented duplicate vector chunks in Neon PostgreSQL (mapped to {existing_fname})",
                    "5": f"Reused {existing_entities} entities & {existing_rels} relationships in Neo4j",
                },
            )
            return {
                "document_id": content_match["document_id"],
                "filename": safe_filename,
                "duplicate_of": existing_fname,
                "chunks_created": existing_chunks,
                "entities_extracted": existing_entities,
                "relationships_extracted": existing_rels,
                "characters_extracted": char_count,
                "ingest_action": "duplicate_content",
                "content_hash": content_hash[:16],
                "action_detail": action_detail,
            }

        # Scenario 3: Updated version of an existing file (same filename, modified content)
        is_updated_version = len(filename_matches) > 0
        replaced_chunks = 0
        if is_updated_version:
            for old_doc in filename_matches:
                old_id = old_doc["document_id"]
                replaced_chunks += delete_document_chunks(user_id=user_id, document_id=old_id)
                try:
                    delete_document_from_graph(user_id=user_id, document_id=old_id)
                except Exception:
                    logger.warning(
                        "Failed to purge previous graph version %s for %s",
                        old_id,
                        safe_filename,
                        exc_info=True,
                    )

        # ── Step 3: Gemini Embedding Generation ──
        _update_progress(
            user_id,
            state="running",
            current_step=3,
            step_name="Gemini Embedding Generation",
            message=(
                f"Updating {safe_filename}: generating 768-dim Gemini embeddings for {num_chunks} chunks…"
                if is_updated_version
                else f"Generating 768-dim Gemini embeddings for {num_chunks} chunks…"
            ),
            step_outputs={
                "2": (
                    f"Created {num_chunks} chunks (replaced {replaced_chunks} old chunks from previous version)"
                    if is_updated_version
                    else f"Created {num_chunks} overlapping semantic chunks"
                )
            },
        )
        embeddings = embed_texts(chunks)

        # ── Step 4: Neon PostgreSQL Vector & Hybrid Storage ──
        _update_progress(
            user_id,
            state="running",
            current_step=4,
            step_name="Neon PostgreSQL Vector & Hybrid Storage",
            message=f"Storing {num_chunks} chunks & vectors in Neon PostgreSQL (pgvector)…",
            step_outputs={"3": f"Generated {len(embeddings)} × 768-dim embedding vectors"},
        )
        number_of_chunks = add_document_chunks(
            user_id=user_id,
            document_id=document_id,
            filename=safe_filename,
            chunks=chunks,
            character_count=char_count,
            precomputed_embeddings=embeddings,
            content_hash=content_hash,
        )

        # ── Step 5: Neo4j Knowledge Graph Extraction ──
        _update_progress(
            user_id,
            state="running",
            current_step=5,
            step_name="Neo4j Knowledge Graph Extraction",
            message="Extracting domain entities & relationships with Gemini into Neo4j…",
            step_outputs={"4": f"Indexed {number_of_chunks} chunks in Neon pgvector + FTS"},
        )

        entities_extracted = 0
        relationships_extracted = 0
        try:
            graph_result = add_document_to_graph(
                user_id=user_id,
                document_id=document_id,
                filename=safe_filename,
                chunks=chunks,
            )
            entities_extracted = graph_result.get("entities_extracted", 0)
            relationships_extracted = graph_result.get("relationships_extracted", 0)

            if entities_extracted > 0 or relationships_extracted > 0:
                update_document_graph_counts(
                    user_id=user_id,
                    document_id=document_id,
                    entity_count=entities_extracted,
                    relationship_count=relationships_extracted,
                )
        except Exception:
            logger.warning(
                "Knowledge Graph ingestion warning for %s",
                safe_filename,
                exc_info=True,
            )

        ingest_action = "updated" if is_updated_version else "created"
        action_detail = (
            f"Updated '{safe_filename}' — replaced previous version in Neon PostgreSQL and Neo4j."
            if is_updated_version
            else f"Indexed new document '{safe_filename}' into Neon PostgreSQL and Neo4j."
        )

        _update_progress(
            user_id,
            state="completed",
            current_step=5,
            step_name="Completed",
            message=action_detail,
            step_outputs={
                "5": f"Extracted {entities_extracted} entities & {relationships_extracted} relationships in Neo4j"
            },
        )

        return {
            "document_id": document_id,
            "filename": safe_filename,
            "chunks_created": number_of_chunks,
            "entities_extracted": entities_extracted,
            "relationships_extracted": relationships_extracted,
            "characters_extracted": char_count,
            "ingest_action": ingest_action,
            "content_hash": content_hash[:16],
            "action_detail": action_detail,
        }

    except Exception:
        _update_progress(
            user_id,
            state="error",
            current_step=_ingestion_progress.get(user_id, {}).get("current_step", 1),
            step_name="Failed",
            message="Document ingestion failed. Please verify the file and try again.",
            filename=safe_filename,
        )
        raise
