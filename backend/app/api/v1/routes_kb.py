"""Knowledge Base & Document Ingestion REST endpoints (/api/v1/documents, API.md Section 3.1)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile, status

from app.config import Settings, get_settings
from app.dependencies import APIException, DbSessionDep, get_active_role, require_admin_role
from app.models.entities import DocumentChunk
from app.repositories.document_repo import DocumentRepository
from app.schemas.common import DocumentStatusEnum, OffsetPaginationMeta, RoleEnum
from app.schemas.documents import (
    ChunkMetadataSchema,
    DocumentChunkItem,
    DocumentChunkListResponse,
    DocumentDeleteResponse,
    DocumentListResponse,
    DocumentSummary,
    DocumentUploadItemResponse,
    DocumentUploadResponse,
)
from app.services.ingestion import (
    ACTIVE_INGESTION_STATUSES,
    IngestionService,
    remove_document_payload,
    to_document_summary,
)

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_FILES_PER_UPLOAD_BATCH: int = 10


def get_ingestion_service(
    session: DbSessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> IngestionService:
    """Provide a request-scoped IngestionService instance."""
    return IngestionService(session=session, settings=settings)


def _to_chunk_item(chunk: DocumentChunk) -> DocumentChunkItem:
    """Convert a DocumentChunk ORM entity into a validated DocumentChunkItem response model."""
    metadata = ChunkMetadataSchema.model_validate(chunk.chunk_metadata or {})
    return DocumentChunkItem(
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        metadata=metadata,
        created_at=chunk.created_at,
    )


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload and enqueue 1-10 documents for ingestion (Admin Only)",
)
@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
async def upload_documents(
    background_tasks: BackgroundTasks,
    _admin: Annotated[RoleEnum, Depends(require_admin_role)],
    service: Annotated[IngestionService, Depends(get_ingestion_service)],
    files: Annotated[list[UploadFile], File(description="1 to 10 .pdf, .md, or .txt files")],
    replace_existing: Annotated[bool, Form()] = False,
) -> DocumentUploadResponse:
    """Validate uploaded files, compute SHA-256 hashes, and start background ingestion."""
    if not files:
        raise APIException(
            status_code=400,
            code="VALIDATION_ERROR",
            message="At least one file must be provided in the 'files' multipart field.",
            details={"field": "files"},
        )
    if len(files) > MAX_FILES_PER_UPLOAD_BATCH:
        raise APIException(
            status_code=400,
            code="VALIDATION_ERROR",
            message=f"A maximum of {MAX_FILES_PER_UPLOAD_BATCH} files may be uploaded per batch.",
            details={"file_count": len(files), "max_files": MAX_FILES_PER_UPLOAD_BATCH},
        )

    uploaded_items: list[DocumentUploadItemResponse] = []
    for upload in files:
        raw_bytes = await upload.read()
        item, should_schedule = await service.stage_upload_file(
            filename=upload.filename or "",
            raw_bytes=raw_bytes,
            content_type=upload.content_type,
            replace_existing=replace_existing,
        )
        uploaded_items.append(item)
        if should_schedule:
            background_tasks.add_task(
                service.run_ingestion_pipeline,
                item.document_id,
                raw_bytes,
            )

    return DocumentUploadResponse(documents=uploaded_items)


@router.get(
    "",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List uploaded documents and corpus summary metrics",
)
async def list_documents(
    session: DbSessionDep,
    _role: Annotated[RoleEnum, Depends(get_active_role)],
    status_filter: Annotated[
        DocumentStatusEnum | None,
        Query(alias="status", description="Optional document lifecycle status filter"),
    ] = None,
    search: Annotated[
        str | None,
        Query(max_length=200, description="Optional substring filter on title or filename"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentListResponse:
    """Return paginated document records and aggregate corpus metrics for Screen 2."""
    doc_repo = DocumentRepository(session)
    docs, total = await doc_repo.list_documents(
        status=status_filter,
        search=search,
        limit=limit,
        offset=offset,
    )
    metrics = await doc_repo.get_corpus_metrics()
    return DocumentListResponse(
        items=[to_document_summary(doc) for doc in docs],
        summary_metrics=metrics,
        pagination=OffsetPaginationMeta.create(total=total, limit=limit, offset=offset),
    )


@router.get(
    "/{document_id}/chunks",
    response_model=DocumentChunkListResponse,
    status_code=status.HTTP_200_OK,
    summary="List ordered deterministic chunks and extracted KG metadata for a document",
)
async def list_document_chunks(
    document_id: UUID,
    session: DbSessionDep,
    _role: Annotated[RoleEnum, Depends(get_active_role)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentChunkListResponse:
    """Retrieve deterministic chunks and extracted KG entities/relationships for the Inspector."""
    doc_repo = DocumentRepository(session)
    doc = await doc_repo.get_by_id(document_id)
    if doc is None:
        raise APIException(
            status_code=404,
            code="DOCUMENT_NOT_FOUND",
            message=f"Document '{document_id}' was not found.",
            details={"document_id": str(document_id)},
        )

    chunks, total = await doc_repo.list_document_chunks(
        document_id=document_id,
        limit=limit,
        offset=offset,
    )
    return DocumentChunkListResponse(
        document=to_document_summary(doc),
        items=[_to_chunk_item(chunk) for chunk in chunks],
        pagination=OffsetPaginationMeta.create(total=total, limit=limit, offset=offset),
    )


@router.post(
    "/{document_id}/reindex",
    response_model=DocumentSummary,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Purge existing chunks/edges and re-run document ingestion (Admin Only)",
)
@router.post(
    "/{document_id}/retry",
    response_model=DocumentSummary,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
async def reindex_document(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    session: DbSessionDep,
    _admin: Annotated[RoleEnum, Depends(require_admin_role)],
    service: Annotated[IngestionService, Depends(get_ingestion_service)],
) -> DocumentSummary:
    """Reset a document to QUEUED and re-run the asynchronous ingestion pipeline."""
    doc_repo = DocumentRepository(session)
    doc = await doc_repo.get_by_id(document_id)
    if doc is None:
        raise APIException(
            status_code=404,
            code="DOCUMENT_NOT_FOUND",
            message=f"Document '{document_id}' was not found.",
            details={"document_id": str(document_id)},
        )
    if doc.status in ACTIVE_INGESTION_STATUSES:
        raise APIException(
            status_code=409,
            code="INGESTION_IN_PROGRESS",
            message=f"Document '{document_id}' is currently in '{doc.status}' state.",
            details={"document_id": str(document_id), "status": doc.status},
        )

    reset_doc = await service.prepare_reindex(document_id)
    target = reset_doc or doc
    background_tasks.add_task(service.run_ingestion_pipeline, document_id)
    return to_document_summary(target)


@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Cascade-delete a document, its chunks, KG edges, and orphaned entities (Admin Only)",
)
async def delete_document(
    document_id: UUID,
    session: DbSessionDep,
    _admin: Annotated[RoleEnum, Depends(require_admin_role)],
) -> DocumentDeleteResponse:
    """Atomically delete a document and prune orphaned Knowledge Graph provenance."""
    doc_repo = DocumentRepository(session)
    doc = await doc_repo.get_by_id(document_id)
    if doc is None:
        raise APIException(
            status_code=404,
            code="DOCUMENT_NOT_FOUND",
            message=f"Document '{document_id}' was not found.",
            details={"document_id": str(document_id)},
        )
    if doc.status in ACTIVE_INGESTION_STATUSES:
        raise APIException(
            status_code=409,
            code="INGESTION_IN_PROGRESS",
            message=f"Document '{document_id}' is currently in '{doc.status}' state.",
            details={"document_id": str(document_id), "status": doc.status},
        )

    deleted = await doc_repo.delete_document_cascade(document_id)
    if deleted is None:
        raise APIException(
            status_code=404,
            code="DOCUMENT_NOT_FOUND",
            message=f"Document '{document_id}' was not found.",
            details={"document_id": str(document_id)},
        )
    remove_document_payload(document_id)
    return deleted

