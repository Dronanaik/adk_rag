"""Six-stage asynchronous document ingestion orchestration service (ARCHITECTURE.md Section 5.1)."""

import asyncio
from typing import cast
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.entities import Document, DocumentChunk
from app.repositories.document_repo import DocumentRepository
from app.repositories.kg_repo import KnowledgeGraphRepository
from app.schemas.common import DocumentStatusEnum
from app.schemas.documents import (
    AllowedMimeType,
    ChunkMetadataSchema,
    DocumentSummary,
    DocumentUploadItemResponse,
)
from app.services.gemini_service import GeminiService
from app.services.kg_extractor import DocumentKgExtractionStats, KnowledgeGraphExtractionService
from app.utils.chunker import TextChunkSpan
from app.utils.document_parser import (
    derive_document_title,
    detect_and_validate_mime_type,
    parse_and_chunk_document,
    sanitize_filename,
)
from app.utils.hashing import compute_sha256_bytes

logger = structlog.get_logger(__name__)

_INGESTION_SEMAPHORE = asyncio.Semaphore(2)
_RAW_DOCUMENT_PAYLOADS: dict[UUID, bytes] = {}

ACTIVE_INGESTION_STATUSES: frozenset[str] = frozenset(
    {
        DocumentStatusEnum.PARSING.value,
        DocumentStatusEnum.CHUNKING.value,
        DocumentStatusEnum.EMBEDDING.value,
        DocumentStatusEnum.EXTRACTING_KG.value,
    }
)


def store_document_payload(document_id: UUID, raw_bytes: bytes) -> None:
    """Cache raw uploaded document bytes in memory for background ingestion and re-indexing."""
    _RAW_DOCUMENT_PAYLOADS[document_id] = raw_bytes


def get_document_payload(document_id: UUID) -> bytes | None:
    """Retrieve cached raw document bytes if available."""
    return _RAW_DOCUMENT_PAYLOADS.get(document_id)


def remove_document_payload(document_id: UUID) -> None:
    """Remove cached raw document bytes when a document is deleted."""
    _RAW_DOCUMENT_PAYLOADS.pop(document_id, None)


def to_document_summary(doc: Document) -> DocumentSummary:
    """Convert a SQLAlchemy Document ORM row into a validated DocumentSummary DTO."""
    return DocumentSummary(
        document_id=doc.document_id,
        title=doc.title,
        filename=doc.filename,
        mime_type=cast(AllowedMimeType, doc.mime_type),
        content_hash=doc.content_hash,
        file_size_bytes=doc.file_size_bytes,
        status=DocumentStatusEnum(doc.status),
        error_message=doc.error_message,
        chunk_count=doc.chunk_count,
        entity_count=doc.entity_count,
        relation_count=doc.relation_count,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


def to_upload_item_response(doc: Document, *, deduplicated_hit: bool) -> DocumentUploadItemResponse:
    """Convert a SQLAlchemy Document ORM row into a DocumentUploadItemResponse DTO."""
    return DocumentUploadItemResponse(
        document_id=doc.document_id,
        title=doc.title,
        filename=doc.filename,
        mime_type=cast(AllowedMimeType, doc.mime_type),
        content_hash=doc.content_hash,
        file_size_bytes=doc.file_size_bytes,
        status=DocumentStatusEnum(doc.status),
        deduplicated_hit=deduplicated_hit,
        created_at=doc.created_at,
    )


class IngestionService:
    """Coordinates file validation, SHA-256 deduplication, and 6-stage ingestion execution."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
        gemini_service: GeminiService | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._gemini = gemini_service or GeminiService(self._settings)
        self._doc_repo = DocumentRepository(session)
        self._kg_repo = KnowledgeGraphRepository(session)
        self._kg_extractor = KnowledgeGraphExtractionService(self._kg_repo, self._gemini)

    async def stage_upload_file(
        self,
        *,
        filename: str,
        raw_bytes: bytes,
        content_type: str | None = None,
        replace_existing: bool = False,
    ) -> tuple[DocumentUploadItemResponse, bool]:
        """Validate file, deduplicate by SHA-256, and stage a QUEUED document record.

        Returns:
            Tuple of (DocumentUploadItemResponse, should_schedule_pipeline).
        """
        clean_name = sanitize_filename(filename)
        mime_type = detect_and_validate_mime_type(
            filename=clean_name,
            raw_bytes=raw_bytes,
            declared_content_type=content_type,
            max_upload_size_mb=self._settings.MAX_UPLOAD_SIZE_MB,
        )
        content_hash = compute_sha256_bytes(raw_bytes)
        existing = await self._doc_repo.get_by_content_hash(content_hash)

        if existing is not None:
            if not replace_existing and existing.status != DocumentStatusEnum.FAILED.value:
                return to_upload_item_response(existing, deduplicated_hit=True), False
            reset_doc = await self._doc_repo.reset_document_for_reindex(existing.document_id)
            target_doc = reset_doc or existing
            store_document_payload(target_doc.document_id, raw_bytes)
            return to_upload_item_response(target_doc, deduplicated_hit=False), True

        title = derive_document_title(clean_name, raw_bytes, mime_type)
        created = await self._doc_repo.create_document(
            title=title,
            filename=clean_name,
            mime_type=mime_type,
            content_hash=content_hash,
            file_size_bytes=len(raw_bytes),
        )
        store_document_payload(created.document_id, raw_bytes)
        return to_upload_item_response(created, deduplicated_hit=False), True

    async def prepare_reindex(self, document_id: UUID) -> Document | None:
        """Preserve fallback text payload if needed and reset document to QUEUED."""
        doc = await self._doc_repo.get_by_id(document_id)
        if doc is None:
            return None

        if get_document_payload(document_id) is None and doc.mime_type != "application/pdf":
            chunks, _ = await self._doc_repo.list_document_chunks(document_id, limit=100, offset=0)
            if chunks:
                reconstructed = "\n\n".join(c.content for c in chunks).encode("utf-8")
                store_document_payload(document_id, reconstructed)

        return await self._doc_repo.reset_document_for_reindex(document_id)

    async def run_ingestion_pipeline(
        self,
        document_id: UUID,
        raw_bytes: bytes | None = None,
    ) -> DocumentSummary | None:
        """Execute PARSING -> CHUNKING -> EMBEDDING -> EXTRACTING_KG -> INDEXED with isolation."""
        async with _INGESTION_SEMAPHORE:
            doc = await self._doc_repo.get_by_id(document_id)
            if doc is None:
                return None

            payload = raw_bytes if raw_bytes is not None else get_document_payload(document_id)
            current_stage = DocumentStatusEnum.PARSING

            try:
                spans = await self._execute_parse_and_chunk(doc, payload)
                current_stage = DocumentStatusEnum.EMBEDDING
                created_chunks = await self._execute_embedding_stage(doc.document_id, spans)

                current_stage = DocumentStatusEnum.EXTRACTING_KG
                kg_stats = await self._execute_kg_extraction_stage(doc, created_chunks)

                indexed_doc = await self._doc_repo.update_status(
                    document_id=doc.document_id,
                    status=DocumentStatusEnum.INDEXED,
                    error_message=None,
                    chunk_count=len(created_chunks),
                    entity_count=kg_stats.entity_count,
                    relation_count=kg_stats.relation_count,
                )
                return to_document_summary(indexed_doc) if indexed_doc else None
            except Exception as exc:
                await self._session.rollback()
                error_msg = f"[{current_stage.value}] {exc}"
                logger.error(
                    "document_ingestion_failed",
                    document_id=str(document_id),
                    failed_stage=current_stage.value,
                    error=str(exc),
                )
                failed_doc = await self._doc_repo.update_status(
                    document_id=document_id,
                    status=DocumentStatusEnum.FAILED,
                    error_message=error_msg,
                )
                return to_document_summary(failed_doc) if failed_doc else None

    async def _execute_parse_and_chunk(
        self,
        doc: Document,
        payload: bytes | None,
    ) -> list[TextChunkSpan]:
        """Run Stage 1 (PARSING) and Stage 2 (CHUNKING) for a document."""
        await self._doc_repo.update_status(doc.document_id, DocumentStatusEnum.PARSING)
        if payload is None:
            raise RuntimeError(
                "Raw document bytes are unavailable in storage for parsing/re-indexing."
            )
        await self._doc_repo.update_status(doc.document_id, DocumentStatusEnum.CHUNKING)
        mime_type = cast(AllowedMimeType, doc.mime_type)
        return parse_and_chunk_document(
            raw_bytes=payload,
            mime_type=mime_type,
            chunk_size=self._settings.DEFAULT_CHUNK_SIZE,
            chunk_overlap=self._settings.DEFAULT_CHUNK_OVERLAP,
        )

    async def _execute_embedding_stage(
        self,
        document_id: UUID,
        spans: list[TextChunkSpan],
    ) -> list[DocumentChunk]:
        """Run Stage 3 (EMBEDDING) and persist deterministic document chunks."""
        await self._doc_repo.update_status(
            document_id,
            DocumentStatusEnum.EMBEDDING,
            chunk_count=len(spans),
        )
        vectors = await self._gemini.embed_texts([span.content for span in spans])
        chunk_rows: list[tuple[int, str, list[float], dict[str, object]]] = []
        for span, vector in zip(spans, vectors, strict=True):
            meta = ChunkMetadataSchema(
                page_number=span.page_number,
                section_heading=span.section_heading,
                char_start=span.char_start,
                char_end=span.char_end,
                token_count=span.token_count,
                extracted_entities=[],
                extracted_relationships=[],
            )
            chunk_rows.append(
                (span.chunk_index, span.content, vector, meta.model_dump(mode="json"))
            )

        created_chunks = await self._doc_repo.insert_chunks(document_id, chunk_rows)
        await self._session.commit()
        return created_chunks

    async def _execute_kg_extraction_stage(
        self,
        doc: Document,
        chunks: list[DocumentChunk],
    ) -> DocumentKgExtractionStats:
        """Run Stage 4 (EXTRACTING_KG) and commit enriched chunk metadata and KG triples."""
        await self._doc_repo.update_status(
            doc.document_id,
            DocumentStatusEnum.EXTRACTING_KG,
            chunk_count=len(chunks),
        )
        kg_stats = await self._kg_extractor.extract_and_persist_for_chunks(
            document_id=doc.document_id,
            document_title=doc.title,
            chunks=chunks,
        )
        await self._session.commit()
        return kg_stats
