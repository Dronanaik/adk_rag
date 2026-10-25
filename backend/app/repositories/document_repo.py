"""Async SQLAlchemy repository for documents, deterministic chunks, and cascading cleanup."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Document, DocumentChunk, KgEntity, KgRelationship
from app.schemas.common import DocumentStatusEnum
from app.schemas.documents import AllowedMimeType, CorpusSummaryMetrics, DocumentDeleteResponse


class DocumentRepository:
    """Data access layer for Table 2 (documents) and Table 3 (document_chunks)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, document_id: UUID) -> Document | None:
        """Return a document by primary key UUID, or None if not found."""
        stmt = select(Document).where(Document.document_id == document_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_content_hash(self, content_hash: str) -> Document | None:
        """Look up an existing document by SHA-256 content_hash for idempotency (NFR-06)."""
        stmt = select(Document).where(Document.content_hash == content_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_document(
        self,
        title: str,
        filename: str,
        mime_type: AllowedMimeType,
        content_hash: str,
        file_size_bytes: int,
    ) -> Document:
        """Insert a new QUEUED document row."""
        doc = Document(
            title=title.strip(),
            filename=filename,
            mime_type=mime_type,
            content_hash=content_hash,
            file_size_bytes=file_size_bytes,
            status=DocumentStatusEnum.QUEUED.value,
        )
        self._session.add(doc)
        await self._session.commit()
        await self._session.refresh(doc)
        return doc

    async def update_status(
        self,
        document_id: UUID,
        status: DocumentStatusEnum,
        error_message: str | None = None,
        chunk_count: int | None = None,
        entity_count: int | None = None,
        relation_count: int | None = None,
    ) -> Document | None:
        """Update document lifecycle status, counts, and optional failure message."""
        doc = await self.get_by_id(document_id)
        if doc is None:
            return None

        doc.status = status.value
        doc.error_message = error_message
        if chunk_count is not None:
            doc.chunk_count = chunk_count
        if entity_count is not None:
            doc.entity_count = entity_count
        if relation_count is not None:
            doc.relation_count = relation_count
        doc.updated_at = datetime.now(UTC)

        await self._session.commit()
        await self._session.refresh(doc)
        return doc

    async def list_documents(
        self,
        status: DocumentStatusEnum | None = None,
        search: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> tuple[list[Document], int]:
        """List documents with optional status/search filters and bounded offset pagination."""
        clamped_limit = min(max(limit, 1), 100)
        clamped_offset = max(offset, 0)

        base_stmt = select(Document)
        count_stmt = select(func.count(Document.document_id))

        if status is not None:
            base_stmt = base_stmt.where(Document.status == status.value)
            count_stmt = count_stmt.where(Document.status == status.value)

        if search is not None and search.strip():
            pattern = f"%{search.strip()}%"
            filter_expr = or_(Document.title.ilike(pattern), Document.filename.ilike(pattern))
            base_stmt = base_stmt.where(filter_expr)
            count_stmt = count_stmt.where(filter_expr)

        total_res = await self._session.execute(count_stmt)
        total_count = int(total_res.scalar_one() or 0)

        stmt = (
            base_stmt.order_by(Document.created_at.desc(), Document.document_id.asc())
            .limit(clamped_limit)
            .offset(clamped_offset)
        )
        rows = await self._session.execute(stmt)
        return list(rows.scalars().all()), total_count

    async def get_corpus_metrics(self) -> CorpusSummaryMetrics:
        """Compute aggregate corpus metrics across documents, chunks, and KG tables."""
        doc_count = await self._session.scalar(select(func.count(Document.document_id)))
        chunk_count = await self._session.scalar(select(func.count(DocumentChunk.chunk_id)))
        entity_count = await self._session.scalar(select(func.count(KgEntity.entity_id)))
        rel_count = await self._session.scalar(select(func.count(KgRelationship.edge_id)))

        return CorpusSummaryMetrics(
            total_documents=int(doc_count or 0),
            total_indexed_chunks=int(chunk_count or 0),
            total_kg_entities=int(entity_count or 0),
            total_kg_relationships=int(rel_count or 0),
        )

    async def insert_chunks(
        self,
        document_id: UUID,
        chunks: list[tuple[int, str, list[float], dict[str, object]]],
    ) -> list[DocumentChunk]:
        """Bulk insert deterministic document chunks with 768-dim embeddings."""
        created: list[DocumentChunk] = []
        for chunk_index, content, embedding, metadata in chunks:
            row = DocumentChunk(
                document_id=document_id,
                chunk_index=chunk_index,
                content=content,
                embedding=embedding,
                chunk_metadata=metadata,
            )
            self._session.add(row)
            created.append(row)

        await self._session.flush()
        return created

    async def list_document_chunks(
        self,
        document_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[DocumentChunk], int]:
        """List chunks for a document ordered deterministically by chunk_index ASC."""
        clamped_limit = min(max(limit, 1), 100)
        clamped_offset = max(offset, 0)

        count_stmt = select(func.count(DocumentChunk.chunk_id)).where(
            DocumentChunk.document_id == document_id
        )
        total_count = int((await self._session.scalar(count_stmt)) or 0)

        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .limit(clamped_limit)
            .offset(clamped_offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total_count

    async def get_chunks_by_ids(
        self,
        chunk_ids: list[UUID],
    ) -> list[tuple[DocumentChunk, str]]:
        """Fetch chunks and their parent document titles for a list of chunk UUIDs."""
        if not chunk_ids:
            return []
        stmt = (
            select(DocumentChunk, Document.title)
            .join(Document, Document.document_id == DocumentChunk.document_id)
            .where(DocumentChunk.chunk_id.in_(chunk_ids))
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await self._session.execute(stmt)
        return [(row[0], str(row[1])) for row in result.all()]

    async def search_chunks_by_vector(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        min_similarity: float = 0.55,
    ) -> list[tuple[DocumentChunk, str, float]]:
        """Retrieve top_k chunks from INDEXED documents ordered by cosine similarity."""
        clamped_k = min(max(top_k, 1), 50)
        distance_expr = DocumentChunk.embedding.cosine_distance(query_embedding)
        similarity_expr = (1.0 - distance_expr).label("similarity")

        stmt = (
            select(DocumentChunk, Document.title, similarity_expr)
            .join(Document, Document.document_id == DocumentChunk.document_id)
            .where(
                Document.status == DocumentStatusEnum.INDEXED.value,
                (1.0 - distance_expr) >= min_similarity,
            )
            .order_by(distance_expr.asc())
            .limit(clamped_k)
        )
        result = await self._session.execute(stmt)
        return [(row[0], str(row[1]), float(row[2])) for row in result.all()]

    async def search_chunks_by_keyword(
        self,
        query_text: str,
        top_k: int = 10,
    ) -> list[tuple[DocumentChunk, str, float]]:
        """Retrieve top_k chunks from INDEXED documents using PostgreSQL full-text search."""
        cleaned_query = query_text.strip()
        if not cleaned_query:
            return []

        clamped_k = min(max(top_k, 1), 50)
        ts_vector = func.to_tsvector("english", DocumentChunk.content)
        ts_query = func.plainto_tsquery("english", cleaned_query)
        rank_expr = func.ts_rank_cd(ts_vector, ts_query).label("fts_rank")

        stmt = (
            select(DocumentChunk, Document.title, rank_expr)
            .join(Document, Document.document_id == DocumentChunk.document_id)
            .where(
                Document.status == DocumentStatusEnum.INDEXED.value,
                ts_vector.op("@@")(ts_query),
            )
            .order_by(rank_expr.desc())
            .limit(clamped_k)
        )
        result = await self._session.execute(stmt)
        return [(row[0], str(row[1]), float(row[2])) for row in result.all()]

    async def _prune_document_from_entities(
        self,
        document_id: UUID,
        chunk_ids: set[UUID],
    ) -> int:
        """Remove document/chunk provenance from kg_entities and delete orphaned nodes."""
        stmt = select(KgEntity).where(KgEntity.source_document_ids.contains([document_id]))
        entities = list((await self._session.execute(stmt)).scalars().all())
        orphaned_ids: list[UUID] = []

        for entity in entities:
            remaining_docs = [d for d in entity.source_document_ids if d != document_id]
            remaining_chunks = [c for c in entity.source_chunk_ids if c not in chunk_ids]
            if not remaining_docs or not remaining_chunks:
                orphaned_ids.append(entity.entity_id)
            else:
                entity.source_document_ids = remaining_docs
                entity.source_chunk_ids = remaining_chunks

        if orphaned_ids:
            await self._session.execute(
                delete(KgEntity).where(KgEntity.entity_id.in_(orphaned_ids))
            )
        return len(orphaned_ids)

    async def delete_document_cascade(
        self,
        document_id: UUID,
    ) -> DocumentDeleteResponse | None:
        """Atomically delete a document, its chunks, KG relationships, and orphaned entities."""
        doc = await self.get_by_id(document_id)
        if doc is None:
            return None

        chunk_rows = await self._session.execute(
            select(DocumentChunk.chunk_id).where(DocumentChunk.document_id == document_id)
        )
        chunk_ids = {row[0] for row in chunk_rows.all()}

        rel_count = int(
            (
                await self._session.scalar(
                    select(func.count(KgRelationship.edge_id)).where(
                        KgRelationship.document_id == document_id
                    )
                )
            )
            or 0
        )

        await self._session.execute(
            delete(KgRelationship).where(KgRelationship.document_id == document_id)
        )
        removed_entities = await self._prune_document_from_entities(document_id, chunk_ids)
        await self._session.delete(doc)
        await self._session.commit()

        return DocumentDeleteResponse(
            deleted_document_id=document_id,
            removed_chunks_count=len(chunk_ids),
            removed_relationships_count=rel_count,
            removed_orphaned_entities_count=removed_entities,
        )

    async def reset_document_for_reindex(self, document_id: UUID) -> Document | None:
        """Purge a document's existing chunks/edges/orphans and reset status to QUEUED."""
        doc = await self.get_by_id(document_id)
        if doc is None:
            return None

        chunk_rows = await self._session.execute(
            select(DocumentChunk.chunk_id).where(DocumentChunk.document_id == document_id)
        )
        chunk_ids = {row[0] for row in chunk_rows.all()}

        await self._session.execute(
            delete(KgRelationship).where(KgRelationship.document_id == document_id)
        )
        await self._prune_document_from_entities(document_id, chunk_ids)
        await self._session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )

        doc.status = DocumentStatusEnum.QUEUED.value
        doc.error_message = None
        doc.chunk_count = 0
        doc.entity_count = 0
        doc.relation_count = 0
        doc.updated_at = datetime.now(UTC)

        await self._session.commit()
        await self._session.refresh(doc)
        return doc
