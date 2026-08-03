# ADK RAG

A document-based Retrieval-Augmented Generation (RAG) system built with:

- Google ADK for the AI agent
- Gemini for embeddings and answer generation
- ChromaDB as the vector database
- FastAPI for document upload APIs
- PyMuPDF for PDF text extraction
- `python-docx` for DOCX text extraction

The system allows users to upload documents, convert them into searchable vector embeddings, and ask questions about their uploaded content.

---

## Features

- Upload PDF, DOCX, TXT, Markdown, CSV, JSON, XML, and HTML files
- Extract text from uploaded documents
- Split documents into overlapping chunks
- Generate Gemini embeddings
- Store chunks and embeddings in ChromaDB
- Search relevant document chunks using semantic similarity
- Use Google ADK to answer questions based on retrieved chunks
- Support user-specific document filtering
- Return source filename and chunk metadata

---

## Architecture

### Document ingestion

```text
User uploads a document
        ↓
FastAPI upload endpoint
        ↓
Text extraction
        ↓
Text chunking
        ↓
Gemini embeddings
        ↓
ChromaDB
Question answering
User asks a question
        ↓
Google ADK agent
        ↓
Search document tool
        ↓
Question embedding
        ↓
ChromaDB similarity search
        ↓
Relevant chunks
        ↓
Gemini-generated answer
Project structure
adk_rag/
├── app/
│   ├── __init__.py
│   ├── agent.py
│   ├── api.py
│   ├── chunking.py
│   ├── config.py
│   ├── database.py
│   ├── embeddings.py
│   ├── ingest.py
│   ├── parsers.py
│   ├── rag_store.py
│   └── run_agent.py
├── data/
│   └── chroma/
├── uploads/
├── .env
├── .gitignore
└── requirements.txt
Requirements
Python 3.10 or later
A Google API key
Internet connection for Gemini API requests
Linux, macOS, or Windows
Check your Python version:

python --version
Installation
1. Clone the repository
git clone <YOUR_REPOSITORY_URL>
cd adk_rag
2. Create a virtual environment
Linux/macOS:

python3 -m venv .venv
source .venv/bin/activate
Windows:

python -m venv .venv
.venv\Scripts\activate
3. Install dependencies
pip install -r requirements.txt
Required packages
The requirements.txt file should contain:

google-adk
google-genai
chromadb
fastapi
uvicorn
python-multipart
python-dotenv
pymupdf
python-docx
Install them manually if required:

pip install google-adk google-genai chromadb fastapi uvicorn python-multipart python-dotenv pymupdf python-docx
Environment configuration
Create a .env file in the project root:

GOOGLE_API_KEY=your_google_api_key

CHROMA_PATH=./data/chroma
COLLECTION_NAME=documents
TOP_K=5
Replace:

your_google_api_key
with your actual Google API key.

Do not commit .env to Git.

Create a .gitignore file:

.venv/
.env
__pycache__/
*.pyc
data/
uploads/
How the vector database works
The project uses ChromaDB's persistent client:

import chromadb

client = chromadb.PersistentClient(
    path="./data/chroma"
)
The database is stored locally in:

./data/chroma
A collection is created automatically:

collection = client.get_or_create_collection(
    name="documents",
    metadata={
        "hnsw:space": "cosine"
    }
)
Each document chunk contains:

A unique chunk ID
The chunk text
An embedding vector
User metadata
Document metadata
Filename
Chunk index
Example metadata:

{
  "user_id": "user_123",
  "document_id": "document_001",
  "filename": "resume.pdf",
  "chunk_index": 2
}
Start the FastAPI server
From the project root, run:

uvicorn app.api:app --reload
The API will be available at:

http://localhost:8000
Swagger API documentation:

http://localhost:8000/docs
ReDoc documentation:

http://localhost:8000/redoc
Check the API health
Run:

curl http://localhost:8000/health
Expected response:

{
  "status": "ok"
}
Upload a document
The upload endpoint is:

POST /documents/upload
Example:

curl -X POST \
  -H "x-user-id: user_123" \
  -F "file=@/absolute/path/to/Drona_Resume.pdf" \
  http://localhost:8000/documents/upload
Example using a file in the current directory:

curl -X POST \
  -H "x-user-id: user_123" \
  -F "file=@./Drona_Resume.pdf" \
  http://localhost:8000/documents/upload
Example using a file in the Downloads directory:

curl -X POST \
  -H "x-user-id: user_123" \
  -F "file=@$HOME/Downloads/Drona_Resume.pdf" \
  http://localhost:8000/documents/upload
Example response:

{
  "success": true,
  "message": "Document ingested successfully.",
  "result": {
    "document_id": "a9be0a7c-1ef9-43a1-bb2a-1208cf2ba7b5",
    "filename": "Drona_Resume.pdf",
    "chunks_created": 8,
    "characters_extracted": 8400
  }
}
Troubleshooting upload errors
If you receive:

curl: (26) Failed to open/read local data from file/application
curl cannot find or read the local file.

Check the current directory:

pwd
ls -lh
Check whether the file exists:

ls -lh ./Drona_Resume.pdf
Search for the file:

find ~ -iname "*resume*.pdf"
Then use the full path:

curl -X POST \
  -H "x-user-id: user_123" \
  -F "file=@/home/your-user/Downloads/Drona_Resume.pdf" \
  http://localhost:8000/documents/upload
Linux filenames are case-sensitive. These filenames are different:

Drona_Resume.pdf
drona_resume.pdf
Drona_resume.pdf
If the filename contains spaces, quote the complete file path:

curl -X POST \
  -H "x-user-id: user_123" \
  -F 'file=@/home/your-user/Downloads/Drona Resume.pdf' \
  http://localhost:8000/documents/upload
Document ingestion process
When a document is uploaded, the following steps occur:

text = extract_text(file_path)
chunks = chunk_text(text)
embeddings = embed_texts(chunks)
add_document_chunks(
    user_id=user_id,
    document_id=document_id,
    filename=filename,
    chunks=chunks,
)
Text extraction
The parser identifies the file type and extracts readable text.

Supported formats include:

.pdf
.docx
.txt
.md
.csv
.json
.xml
.html
.htm
.log
Scanned PDFs and images require OCR. Text extraction alone will not work for image-only documents.

Chunking
Documents are divided into smaller overlapping sections.

Example configuration:

chunks = chunk_text(
    text,
    chunk_size=1200,
    overlap=200,
)
Where:

chunk_size is the maximum chunk size
overlap prevents information from being lost between chunks
The overlap is useful when a sentence or concept crosses two chunk boundaries.

Embeddings
The system uses the Gemini embedding model:

EMBEDDING_MODEL = "gemini-embedding-001"
The same embedding model must be used for:

Document chunks
User questions
Example:

response = client.models.embed_content(
    model="gemini-embedding-001",
    contents=text,
    config=EmbedContentConfig(
        output_dimensionality=768,
    ),
)
Do not change the embedding model or embedding dimension for an existing collection without re-indexing the documents.

Search ChromaDB directly
You can search the vector database from Python:

from app.rag_store import search_documents

matches = search_documents(
    user_id="user_123",
    query="What are the user's technical skills?",
    top_k=5,
)

for match in matches:
    print(match["text"])
    print(match["metadata"])
    print(match["distance"])
The search uses the user_id filter:

where={
    "user_id": user_id,
}
This prevents a user from retrieving another user's documents.

Google ADK integration
The ADK agent uses a tool called:

search_user_documents
The tool performs the following operations:

Receive the user query
        ↓
Read the authenticated user ID
        ↓
Generate a query embedding
        ↓
Search ChromaDB
        ↓
Return relevant chunks
The agent is configured to:

Search uploaded documents
Answer using retrieved chunks
Avoid inventing information
Tell the user when information is not found
Include source citations
Example answer:

The candidate has experience with Python, FastAPI, and Google ADK.

[Source: Drona_Resume.pdf, chunk 2]
Run the ADK agent manually
If app/run_agent.py is available, run:

python -m app.run_agent
The agent should:

Create an ADK session
Receive a question
Call the document search tool
Retrieve relevant chunks from ChromaDB
Generate an answer
Example question:

What programming languages are mentioned in my resume?
ChromaDB operations
Check the number of stored chunks
from app.database import collection

print(collection.count())
View stored records
records = collection.get(
    limit=10,
    include=[
        "documents",
        "metadatas",
    ],
)

print(records)
Delete a document
from app.database import collection

collection.delete(
    where={
        "$and": [
            {"user_id": "user_123"},
            {"document_id": "document_001"},
        ]
    }
)
Delete the entire collection
from app.database import client

client.delete_collection(
    name="documents"
)
Warning: deleting a collection permanently removes all document chunks and embeddings.

Security
The example uses:

x-user-id: user_123
This is only suitable for local testing.

For production, use a real authentication system, such as:

Firebase Authentication
Google Identity Platform
OAuth
JWT
Session-based authentication
Google Cloud IAM
The server should determine the user ID from a validated authentication token.

Do not allow the language model to choose the user ID.

Always apply user filtering during retrieval:

where={
    "user_id": authenticated_user_id,
}
Supported document types
The basic parser supports:

File type	Parser
PDF	PyMuPDF
DOCX	python-docx
TXT	Python file reader
Markdown	Python file reader
CSV	Python file reader
JSON	Python file reader
XML	Python file reader
HTML	Python file reader
For additional formats, consider:

openpyxl for Excel files
python-pptx for PowerPoint files
Tesseract OCR for images and scanned PDFs
Google Document AI for enterprise document processing
Unstructured for multi-format document extraction
Common issues
ChromaDB contains no records
Check that:

The upload completed successfully.
Text was extracted from the document.
Chunks were created.
Embeddings were generated.
The data/chroma directory exists.
Check the collection count:

from app.database import collection

print(collection.count())
No text extracted from the PDF
The PDF may be scanned or image-based.

Use OCR, such as:

Tesseract
Google Document AI
Cloud Vision API
Search returns irrelevant chunks
Try:

Improving the chunk size
Increasing overlap
Using more specific queries
Adding metadata filters
Adding a similarity threshold
Using hybrid keyword and vector search
Adding a reranking step
API connection error
If you receive:

curl: (7) Failed to connect to localhost port 8000
Start the API:

uvicorn app.api:app --reload
Gemini API authentication error
Check that:

echo $GOOGLE_API_KEY
returns a value.

Also check that the .env file exists in the project root:

ls -la .env
Production recommendations
For production deployments, consider:

Persistent hosted vector storage
PostgreSQL with pgvector
Vertex AI Vector Search
AlloyDB with vector search
Cloud Storage for original documents
Pub/Sub for asynchronous ingestion
Cloud Run for API and worker services
OCR for scanned documents
Authentication and authorization
File size restrictions
Virus scanning
Rate limiting
Monitoring and logging
Document deletion and retention policies
Retrieval evaluation
A production architecture may look like this:

Cloud Storage
        ↓
Upload API
        ↓
Pub/Sub
        ↓
Ingestion Worker
        ↓
Document Parser / OCR
        ↓
Gemini Embeddings
        ↓
Vertex AI Vector Search or AlloyDB
        ↓
Google ADK Agent
        ↓
User Answer
License
Add your project license here.

Example:

MIT License
Author
Created by Drona.


Save the file using the exact filename:

```text
README.md
The standard filename is README.md, not README.md. Then add and commit it:

git add README.md
git commit -m "Add ADK RAG documentation"