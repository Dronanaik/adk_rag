import logging
import time
import uuid
from typing import Any

from app.chunking import chunk_text
from app.embeddings import embed_texts
from app.graph_store import add_document_to_graph
from app.parsers import extract_text
from app.rag_store import add_document_chunks, update_document_graph_counts

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
            "step_outputs": {},
        },
    )


def ingest_document(
    file_path: str,
    filename: str,
    user_id: str,
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
    _ingestion_progress[user_id] = {"step_outputs": {}, "filename": safe_filename}

    try:
        # ── Step 1: Text Extraction ──
        _update_progress(
            user_id,
            state="running",
            current_step=1,
            step_name="Text Extraction",
            message=f"Extracting raw text from {safe_filename}…",
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
            message=f"Splitting {char_count:,} characters into semantic paragraphs & chunks…",
            step_outputs={"1": f"Extracted {char_count:,} characters from {safe_filename}"},
        )

        # ── Step 2: Semantic Chunking ──
        chunks = chunk_text(
            text,
            chunk_size=1200,
            overlap=200,
        )
        num_chunks = len(chunks)

        # ── Step 3: Gemini Embedding Generation ──
        _update_progress(
            user_id,
            state="running",
            current_step=3,
            step_name="Gemini Embedding Generation",
            message=f"Generating 768-dim Gemini embeddings for {num_chunks} chunks…",
            step_outputs={"2": f"Created {num_chunks} overlapping semantic chunks"},
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

        _update_progress(
            user_id,
            state="completed",
            current_step=5,
            step_name="Completed",
            message=f"Finished ingesting {safe_filename} into Neon PostgreSQL and Neo4j.",
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
