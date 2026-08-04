import asyncio
import os
import shutil
import uuid

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from app.agent import root_agent
from app.ingest import ingest_document
from app.rag_store import (
    delete_document_chunks,
    list_user_documents,
)
from app.parsers import extract_text
from app.database import index as pc_index

app = FastAPI(
    title="Google ADK RAG API",
    description="Document-based RAG system powered by Google ADK, Gemini, and ChromaDB.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS — allow all origins for local development.
# In production, replace "*" with your actual frontend domain.
# ---------------------------------------------------------------------------
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS")
if allowed_origins_env:
    allow_origins = [origin.strip() for origin in allowed_origins_env.split(",")]
else:
    allow_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIRECTORY = "./uploads"
APP_NAME = "document_rag_app"

os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

# ---------------------------------------------------------------------------
# ADK session service — shared across all requests (in-memory).
# Each user gets their own session keyed by (user_id, session_id).
# ---------------------------------------------------------------------------
_session_service = InMemorySessionService()
_runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=_session_service,
)

# Supported file types (for the /ingest/status endpoint)
SUPPORTED_FILE_TYPES = [
    ".pdf",
    ".docx",
    ".xlsx",
    ".xls",
    ".pptx",
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".xml",
    ".html",
    ".htm",
    ".log",
]


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str
    session_id: str | None = None


class QueryResponse(BaseModel):
    answer: str
    session_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok"}


@app.get("/ingest/status")
async def ingest_status():
    """
    Return basic ingestion pipeline status:
    total chunks stored, supported file types, and pipeline state.
    """
    try:
        stats = pc_index.describe_index_stats()
        if hasattr(stats, 'total_vector_count'):
            total_chunks = stats.total_vector_count
        elif isinstance(stats, dict):
            total_chunks = stats.get("total_vector_count", 0)
        else:
            total_chunks = 0
        status = "ready"
    except Exception as error:
        total_chunks = -1
        status = f"error: {error}"

    return {
        "status": status,
        "total_chunks": total_chunks,
        "supported_file_types": SUPPORTED_FILE_TYPES,
        "pipeline_steps": [
            "1. Text extraction (parser)",
            "2. Text normalization & chunking",
            "3. Gemini embedding generation (gemini-embedding-001)",
            "4. Pinecone vector storage",
        ],
    }


@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    x_user_id: str = Header(..., alias="x-user-id"),
):
    """
    Upload and ingest a document for the given user.

    Supported formats: PDF, DOCX, XLSX, XLS, PPTX, TXT, MD, CSV, JSON, XML, HTML, HTM, LOG.

    In production, replace the x-user-id header with a real authentication system.
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required.",
        )

    file_extension = os.path.splitext(file.filename)[1].lower()

    if file_extension not in SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type: '{file_extension}'. "
                f"Supported types: {', '.join(SUPPORTED_FILE_TYPES)}"
            ),
        )

    temporary_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIRECTORY, temporary_filename)

    try:
        with open(file_path, "wb") as output_file:
            shutil.copyfileobj(file.file, output_file)

        result = ingest_document(
            file_path=file_path,
            filename=file.filename,
            user_id=x_user_id,
        )

        return {
            "success": True,
            "message": "Document ingested successfully.",
            "result": result,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Document ingestion failed: {error}",
        )

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@app.get("/documents")
def get_documents(
    x_user_id: str = Header(..., alias="x-user-id"),
):
    """List all documents uploaded by the given user."""
    documents = list_user_documents(x_user_id)

    return {
        "success": True,
        "documents": documents,
    }


@app.delete("/documents/{document_id}")
def delete_document(
    document_id: str,
    x_user_id: str = Header(..., alias="x-user-id"),
):
    """Delete all chunks of a specific document for the given user."""
    deleted_chunks = delete_document_chunks(
        user_id=x_user_id,
        document_id=document_id,
    )

    if deleted_chunks == 0:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    return {
        "success": True,
        "document_id": document_id,
        "deleted_chunks": deleted_chunks,
    }


@app.post("/chat", response_model=QueryResponse)
async def chat(
    request: QueryRequest,
    x_user_id: str = Header(..., alias="x-user-id"),
):
    """
    Send a question to the ADK RAG agent and get an answer based on the
    user's uploaded documents.

    Optionally pass a session_id to continue an existing conversation.
    If omitted, a new session is created automatically.
    """

    user_id = x_user_id

    # Create or reuse an ADK session
    session_id = request.session_id

    if session_id:
        # Try to get existing session; fall back to creating a new one
        try:
            session = await _session_service.get_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
            )
            if session is None:
                raise ValueError("Session not found")
        except Exception:
            session = await _session_service.create_session(
                app_name=APP_NAME,
                user_id=user_id,
            )
    else:
        session = await _session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
        )

    message = types.Content(
        role="user",
        parts=[types.Part(text=request.query)],
    )

    answer_text = ""

    try:
        async for event in _runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=message,
        ):
            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        answer_text += part.text
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {error}",
        )

    if not answer_text:
        answer_text = "I could not generate a response. Please try again."

    return QueryResponse(
        answer=answer_text,
        session_id=session.id,
    )
