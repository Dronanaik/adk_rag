from pinecone import Pinecone

from app.config import PINECONE_API_KEY, PINECONE_INDEX_NAME

pc = Pinecone(api_key=PINECONE_API_KEY)

# Note: The index must be created manually or handled in a setup script.
# We assume it already exists for the RAG system and uses the dimension of our embedding model (e.g. 768 for gemini-embedding).
index = pc.Index(PINECONE_INDEX_NAME)