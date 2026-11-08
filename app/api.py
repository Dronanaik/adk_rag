import asyncio
from contextlib import asynccontextmanager
import logging
import os
import shutil
import tempfile
import uuid

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from app.agent import root_agent
from app.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_user_by_id,
    register_user,
)
import app.config as config
from app.config import (
    get_env_settings_payload,
    reset_runtime_config,
    update_runtime_config,
)
from app.database import (
    close_all_databases,
    init_all_databases,
    reload_database_connections,
)
from app.embeddings import reset_genai_client
from app.graph_store import (
    delete_all_user_documents_from_graph,
    delete_document_from_graph,
    get_entity_relationships_from_graph,
    get_graph_stats,
    get_user_knowledge_graph,
    reset_neo4j_schema_flag,
    search_knowledge_graph,
)
from app.ingest import get_ingestion_progress, ingest_document
from app.rag_store import (
    delete_all_user_documents,
    delete_document_chunks,
    get_vector_store_stats,
    list_user_documents,
)

logger = logging.getLogger(__name__)


def _sanitize_log_value(value: str) -> str:
    """Strip CR/LF characters from user-provided values before logging."""
    return str(value).replace("\r", "").replace("\n", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_all_databases()
    yield
    close_all_databases()


app = FastAPI(
    title="ADK Agentic RAG + Knowledge Graph API",
    description=(
        "Hybrid Agentic RAG & Knowledge Graph platform powered by Google ADK, "
        "Gemini, Neon PostgreSQL (pgvector), and Neo4j."
    ),
    version="2.3.3",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow all origins for local development.
# In production, set ALLOWED_ORIGINS to your frontend domain.
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

UPLOAD_DIRECTORY = os.path.realpath(os.path.join(tempfile.gettempdir(), "adk_rag_uploads"))
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
SAFE_EXTENSION_MAP = {ext: ext for ext in SUPPORTED_FILE_TYPES}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class SignUpRequest(BaseModel):
    full_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class QueryRequest(BaseModel):
    query: str
    session_id: str | None = None


class QueryResponse(BaseModel):
    answer: str
    session_id: str
    tools_used: list[str] = []


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok"}


@app.post("/auth/signup")
def auth_signup(request: SignUpRequest):
    """
    Create a new user account in Neon PostgreSQL and return a signed JWT session token.
    """
    try:
        user = register_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
        )
        token = create_access_token(user)
        return {
            "success": True,
            "user": user,
            "access_token": token,
            "token_type": "bearer",
        }
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid registration details provided.",
        )
    except Exception:
        logger.exception("Unexpected error during user registration")
        raise HTTPException(
            status_code=500,
            detail="Registration failed due to an internal server error.",
        )


@app.post("/auth/login")
def auth_login(request: LoginRequest):
    """
    Authenticate an existing user against Neon PostgreSQL and return a signed JWT session token.
    """
    try:
        user = authenticate_user(
            email=request.email,
            password=request.password,
        )
        token = create_access_token(user)
        return {
            "success": True,
            "user": user,
            "access_token": token,
            "token_type": "bearer",
        }
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )
    except Exception:
        logger.exception("Unexpected error during user authentication")
        raise HTTPException(
            status_code=500,
            detail="Authentication failed due to an internal server error.",
        )


@app.get("/auth/me")
def auth_me(current_user: dict = Depends(get_current_user)):
    """
    Verify current Bearer JWT token and return the authenticated user's profile from Neon PostgreSQL.
    """
    try:
        db_user = get_user_by_id(current_user["id"])
        if db_user:
            return {"success": True, "user": db_user}
    except Exception:
        logger.debug("Could not refresh user profile from database", exc_info=True)
    return {
        "success": True,
        "user": {
            "id": current_user["id"],
            "email": current_user["email"],
            "full_name": current_user["full_name"],
        },
    }


@app.get("/ingest/status")
async def ingest_status():
    """
    Return hybrid ingestion pipeline status:
    Neon PostgreSQL (pgvector) chunk/document counts + Neo4j entity/relationship counts.
    """
    try:
        pg_stats = get_vector_store_stats()
        total_chunks = pg_stats.get("total_chunks", 0)
        total_documents = pg_stats.get("total_documents", 0)
        postgres_status = "ready"
    except Exception:
        logger.warning("Neon PostgreSQL status check failed", exc_info=True)
        total_chunks = 0
        total_documents = 0
        postgres_status = "error"

    try:
        graph_stats = get_graph_stats()
        neo4j_status = graph_stats.get("status", "ready")
        total_entities = graph_stats.get("total_entities", 0)
        total_relationships = graph_stats.get("total_relationships", 0)
    except Exception:
        logger.warning("Neo4j status check failed", exc_info=True)
        neo4j_status = "error"
        total_entities = 0
        total_relationships = 0

    overall_status = "ready" if postgres_status == "ready" else "error"

    return {
        "status": overall_status,
        "postgres_status": postgres_status,
        "neo4j_status": neo4j_status,
        "total_chunks": total_chunks,
        "total_documents": total_documents,
        "total_entities": total_entities,
        "total_relationships": total_relationships,
        "supported_file_types": SUPPORTED_FILE_TYPES,
        "pipeline_steps": [
            "1. Text extraction (format-specific parser)",
            "2. Structure-aware semantic chunking",
            "3. Gemini embedding generation (gemini-embedding-001, 768-dim)",
            "4. Neon PostgreSQL vector & full-text storage (pgvector + tsvector)",
            "5. Neo4j Knowledge Graph entity & relationship extraction (Gemini Structured Outputs)",
        ],
    }


@app.get("/ingest/progress")
async def ingest_progress(
    current_user: dict = Depends(get_current_user),
):
    """
    Return real-time step-by-step ingestion progress (Steps 1..5) for the current user.
    """
    return get_ingestion_progress(current_user["user_id"])


@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    doc_index: int = Query(default=1, ge=1),
    total_docs: int = Query(default=1, ge=1),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload and ingest a document into both Neon PostgreSQL (pgvector) and Neo4j Knowledge Graph.
    Runs the ingestion pipeline in a background worker thread so live step progress
    (/ingest/progress) can be polled concurrently without blocking the event loop.
    """
    user_id = current_user["user_id"]

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required.",
        )

    clean_filename = os.path.basename(file.filename).replace("\r", "").replace("\n", "")
    raw_extension = os.path.splitext(clean_filename)[1].lower()
    safe_extension = SAFE_EXTENSION_MAP.get(raw_extension)

    if not safe_extension:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type. "
                f"Supported types: {', '.join(SUPPORTED_FILE_TYPES)}"
            ),
        )

    temporary_filename = f"{uuid.uuid4()}{safe_extension}"
    file_path = os.path.realpath(os.path.join(UPLOAD_DIRECTORY, temporary_filename))
    if not file_path.startswith(UPLOAD_DIRECTORY + os.sep):
        raise HTTPException(status_code=400, detail="Invalid upload file path.")

    try:
        with open(file_path, "wb") as output_file:
            shutil.copyfileobj(file.file, output_file)

        result = await asyncio.to_thread(
            ingest_document,
            file_path=file_path,
            filename=clean_filename,
            user_id=user_id,
            doc_index=doc_index,
            total_docs=total_docs,
        )

        return {
            "success": True,
            "message": result.get(
                "action_detail",
                "Document ingested into Neon PostgreSQL and Neo4j Knowledge Graph.",
            ),
            "result": result,
        }

    except HTTPException:
        raise

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="No readable text was found in the uploaded document.",
        )

    except Exception:
        logger.exception("Document ingestion failed for file %s", _sanitize_log_value(clean_filename))
        raise HTTPException(
            status_code=500,
            detail="Document ingestion failed due to an internal server error.",
        )

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@app.get("/documents")
def get_documents(
    current_user: dict = Depends(get_current_user),
):
    """List all documents uploaded by the authenticated user."""
    documents = list_user_documents(current_user["user_id"])

    return {
        "success": True,
        "documents": documents,
    }


@app.delete("/documents")
def delete_all_documents(
    current_user: dict = Depends(get_current_user),
):
    """
    Delete all documents, vector chunks, and Knowledge Graph entities/relationships
    belonging to the authenticated user.
    """
    user_id = current_user["user_id"]
    pg_deleted = delete_all_user_documents(user_id=user_id)

    graph_deleted = {"deleted_relationships": 0, "deleted_entities": 0}
    try:
        graph_deleted = delete_all_user_documents_from_graph(user_id=user_id)
    except Exception:
        logger.warning(
            "Neo4j delete-all warning for user %s",
            _sanitize_log_value(user_id),
            exc_info=True,
        )

    return {
        "success": True,
        "deleted_documents": pg_deleted.get("deleted_documents", 0),
        "deleted_chunks": pg_deleted.get("deleted_chunks", 0),
        "deleted_entities": graph_deleted.get("deleted_entities", 0),
        "deleted_relationships": graph_deleted.get("deleted_relationships", 0),
    }


@app.delete("/documents/{document_id}")
def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Delete a document's chunks from Neon PostgreSQL and its entities/relationships from Neo4j.
    """
    user_id = current_user["user_id"]
    deleted_chunks = delete_document_chunks(
        user_id=user_id,
        document_id=document_id,
    )

    graph_deleted = {"deleted_relationships": 0, "deleted_entities": 0}
    try:
        graph_deleted = delete_document_from_graph(
            user_id=user_id,
            document_id=document_id,
        )
    except Exception:
        logger.warning(
            "Neo4j delete warning for document %s",
            _sanitize_log_value(document_id),
            exc_info=True,
        )

    if deleted_chunks == 0 and graph_deleted.get("deleted_relationships", 0) == 0:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    return {
        "success": True,
        "document_id": document_id,
        "deleted_chunks": deleted_chunks,
        "deleted_entities": graph_deleted.get("deleted_entities", 0),
        "deleted_relationships": graph_deleted.get("deleted_relationships", 0),
    }


@app.get("/graph")
def get_graph(
    q: str | None = Query(default=None, description="Optional search query for filtering graph"),
    current_user: dict = Depends(get_current_user),
):
    """
    Fetch the user's Neo4j Knowledge Graph nodes and relationships for the UI explorer.
    If `q` is provided, also returns matching search results.
    """
    user_id = current_user["user_id"]
    try:
        graph_data = get_user_knowledge_graph(user_id=user_id)
        if q and q.strip():
            search_res = search_knowledge_graph(user_id=user_id, query=q.strip(), limit=25)
            graph_data["search_results"] = search_res
        return {
            "success": True,
            **graph_data,
        }
    except Exception:
        logger.exception("Failed to query Neo4j Knowledge Graph")
        raise HTTPException(
            status_code=500,
            detail="Failed to query the Neo4j Knowledge Graph.",
        )


@app.get("/graph/entity/{entity_name}")
def get_entity_details(
    entity_name: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve direct relationships and connected entities for a specific entity in Neo4j.
    """
    try:
        result = get_entity_relationships_from_graph(
            user_id=current_user["user_id"],
            entity_name=entity_name,
            limit=30,
        )
        return {
            "success": True,
            **result,
        }
    except Exception:
        logger.exception("Failed to query entity relationships")
        raise HTTPException(
            status_code=500,
            detail="Failed to query entity relationships from the Knowledge Graph.",
        )


@app.post("/chat", response_model=QueryResponse)
async def chat(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Send a question to the Google ADK Agentic RAG + Knowledge Graph agent.
    """
    user_id = current_user["user_id"]
    session_id = request.session_id

    if session_id:
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
    tools_used: list[str] = []

    try:
        async for event in _runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=message,
        ):
            # Track which Agentic RAG / Graph tools were invoked
            if event.content and event.content.parts:
                for part in event.content.parts:
                    fn_call = getattr(part, "function_call", None)
                    if fn_call and getattr(fn_call, "name", None):
                        if fn_call.name not in tools_used:
                            tools_used.append(fn_call.name)

            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        answer_text += part.text
    except Exception:
        logger.exception("ADK Agent execution error")
        raise HTTPException(
            status_code=500,
            detail="The AI agent encountered an error while processing your request.",
        )

    if not answer_text:
        answer_text = "I could not generate a response. Please try again."

    return QueryResponse(
        answer=answer_text,
        session_id=session.id,
        tools_used=tools_used,
    )


class EnvSettingsUpdateRequest(BaseModel):
    values: dict[str, str | None] = {}
    persist_to_env: bool = False


def _evaluate_connection_statuses() -> dict[str, str]:
    gemini_status = "ready" if bool(config.GOOGLE_API_KEY) else "unconfigured"

    if not config.DATABASE_URL:
        postgres_status = "unconfigured"
    else:
        try:
            get_vector_store_stats()
            postgres_status = "ready"
        except Exception:
            postgres_status = "error"

    if not (config.NEO4J_URI and config.NEO4J_PASSWORD):
        neo4j_status = "unconfigured"
    else:
        try:
            g_stats = get_graph_stats()
            neo4j_status = g_stats.get("status", "ready")
        except Exception:
            neo4j_status = "error"

    return {
        "gemini": gemini_status,
        "postgres": postgres_status,
        "neo4j": neo4j_status,
    }


@app.get("/settings/env")
def get_environment_settings():
    """
    Return all connection environment variables, their current source ('default' vs 'custom'),
    default fallback previews, documentation anchor links, and live connection statuses.
    """
    return {
        "success": True,
        "variables": get_env_settings_payload(),
        "connections": _evaluate_connection_statuses(),
        "docs_url": config.DOCS_BASE_URL,
    }


@app.post("/settings/env")
def update_environment_settings(request: EnvSettingsUpdateRequest):
    """
    Update connection environment variables manually from the UI.
    Any variable left blank automatically falls back to the default value.
    """
    variables = update_runtime_config(
        values=request.values,
        persist_to_env=request.persist_to_env,
    )
    reset_genai_client()
    reset_neo4j_schema_flag()
    root_agent.model = config.AGENT_MODEL
    reload_database_connections()

    return {
        "success": True,
        "message": (
            "Environment variables applied and saved to .env (blank fields using default fallback)."
            if request.persist_to_env
            else "Environment variables applied (blank fields automatically fell back to default)."
        ),
        "variables": variables,
        "connections": _evaluate_connection_statuses(),
    }


@app.post("/settings/env/reset")
def reset_environment_settings():
    """
    Reset all environment variables back to their default (.env / built-in) values.
    """
    variables = reset_runtime_config()
    reset_genai_client()
    reset_neo4j_schema_flag()
    root_agent.model = config.AGENT_MODEL
    reload_database_connections()

    return {
        "success": True,
        "message": "All environment variables reset to default values.",
        "variables": variables,
        "connections": _evaluate_connection_statuses(),
    }

