import os

from dotenv import load_dotenv

load_dotenv()

# Google Gemini / ADK settings
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
AGENT_MODEL = os.getenv("AGENT_MODEL", "gemini-2.5-pro")
GRAPH_EXTRACTION_MODEL = os.getenv("GRAPH_EXTRACTION_MODEL", "gemini-2.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))

# Neon PostgreSQL (pgvector) settings
DATABASE_URL = os.getenv("DATABASE_URL", "")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "168"))  # 7 days default

# Neo4j Knowledge Graph settings
NEO4J_URI = os.getenv("NEO4J_URI", "")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# Retrieval settings
TOP_K = int(os.getenv("TOP_K", "5"))
