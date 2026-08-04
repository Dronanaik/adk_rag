import os
import shutil
import uuid

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from pydantic import BaseModel

from app.agent import root_agent
from app.ingest import ingest_document
from app.rag_store import (
    delete_document_chunks,
    list_user_documents,
)

app = FastAPI(
    title="Google ADK RAG API"
)

UPLOAD_DIRECTORY = "./uploads"

os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

class QueryRequest(BaseModel):
    query: str

@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    x_user_id: str = Header(...),
):
    """
    Upload and ingest a document.

    In production, replace x-user-id with a real authentication system.
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required.",
        )

    file_extension = os.path.splitext(file.filename)[1]
    temporary_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(
        UPLOAD_DIRECTORY,
        temporary_filename,
    )

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

@app.get("/health")
async def health():
    return {
        "status": "ok"
    }


@app.get("/documents")
def get_documents(
    x_user_id: str = Header(..., alias="x-user-id"),
):
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


