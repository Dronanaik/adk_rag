import os
from pathlib import Path
import re
from typing import Any

from dotenv import load_dotenv

load_dotenv()

DOCS_BASE_URL = "https://dronanaik.github.io/adk_rag/INSTALLATION/"

# Built-in system defaults when not present in .env
SYSTEM_FALLBACKS: dict[str, str] = {
    "GOOGLE_API_KEY": "",
    "AGENT_MODEL": "gemini-2.5-pro",
    "GRAPH_EXTRACTION_MODEL": "gemini-2.5-flash",
    "EMBEDDING_MODEL": "gemini-embedding-001",
    "EMBEDDING_DIMENSIONS": "768",
    "DATABASE_URL": "",
    "JWT_SECRET_KEY": "adk-rag-default-jwt-secret-key-change-in-production",
    "JWT_EXPIRE_HOURS": "168",
    "NEO4J_URI": "",
    "NEO4J_USERNAME": "neo4j",
    "NEO4J_PASSWORD": "",
    "NEO4J_DATABASE": "neo4j",
    "TOP_K": "5",
}

# Snapshot of the initial default environment (.env + system fallbacks)
DEFAULT_CONFIG: dict[str, str] = {
    key: (os.getenv(key) or default_val).strip()
    for key, default_val in SYSTEM_FALLBACKS.items()
}

# Active runtime overrides entered manually via the UI Settings page
_runtime_overrides: dict[str, str] = {}

ENV_VAR_DEFINITIONS: list[dict[str, Any]] = [
    {
        "key": "GOOGLE_API_KEY",
        "label": "Google Gemini API Key",
        "group": "gemini",
        "is_secret": True,
        "placeholder": "AIzaSy...",
        "description": "API key from Google AI Studio used by Gemini 2.5 Pro/Flash and gemini-embedding-001.",
        "doc_url": f"{DOCS_BASE_URL}#1-google_api_key-google-ai-studio",
    },
    {
        "key": "AGENT_MODEL",
        "label": "ADK Agent Reasoning Model",
        "group": "gemini",
        "is_secret": False,
        "placeholder": "gemini-2.5-pro",
        "description": "Primary Gemini model powering the Google ADK multi-tool reasoning agent.",
        "doc_url": f"{DOCS_BASE_URL}#2-agent_model-adk-reasoning-model",
    },
    {
        "key": "GRAPH_EXTRACTION_MODEL",
        "label": "Knowledge Graph Extraction Model",
        "group": "gemini",
        "is_secret": False,
        "placeholder": "gemini-2.5-flash",
        "description": "Fast structured-output Gemini model used in Step 5 to extract entities and relationships.",
        "doc_url": f"{DOCS_BASE_URL}#3-graph_extraction_model-neo4j-extractor-model",
    },
    {
        "key": "EMBEDDING_MODEL",
        "label": "Vector Embedding Model",
        "group": "gemini",
        "is_secret": False,
        "placeholder": "gemini-embedding-001",
        "description": "Gemini embedding model producing 768-dimensional vectors for Neon pgvector.",
        "doc_url": f"{DOCS_BASE_URL}#4-embedding_model-vector-embedding-model",
    },
    {
        "key": "DATABASE_URL",
        "label": "Neon PostgreSQL Connection URI",
        "group": "postgres",
        "is_secret": True,
        "placeholder": "postgresql://user:password@ep-xxx.aws.neon.tech/neondb?sslmode=require",
        "description": "Serverless PostgreSQL connection string with pgvector & Full-Text Search.",
        "doc_url": f"{DOCS_BASE_URL}#5-database_url-neon-console-postgresql",
    },
    {
        "key": "JWT_SECRET_KEY",
        "label": "JWT Signing Secret Key",
        "group": "postgres",
        "is_secret": True,
        "placeholder": "64-char hex secret key",
        "description": "HMAC-SHA256 secret key used to sign and verify Bearer authentication tokens.",
        "doc_url": f"{DOCS_BASE_URL}#6-jwt_secret_key--jwt_expire_hours-authentication-security",
    },
    {
        "key": "JWT_EXPIRE_HOURS",
        "label": "JWT Session Expiration (Hours)",
        "group": "postgres",
        "is_secret": False,
        "placeholder": "168",
        "description": "Lifetime of signed user authentication tokens in hours (default: 168 = 7 days).",
        "doc_url": f"{DOCS_BASE_URL}#6-jwt_secret_key--jwt_expire_hours-authentication-security",
    },
    {
        "key": "NEO4J_URI",
        "label": "Neo4j AuraDB / Bolt URI",
        "group": "neo4j",
        "is_secret": False,
        "placeholder": "neo4j+s://xxxxxxxx.databases.neo4j.io",
        "description": "Connection URI for Neo4j AuraDB (neo4j+s://...) or local Neo4j (bolt://localhost:7687).",
        "doc_url": f"{DOCS_BASE_URL}#7-neo4j_uri-neo4j_username-neo4j_password--neo4j_database-neo4j-auradb",
    },
    {
        "key": "NEO4J_USERNAME",
        "label": "Neo4j Username",
        "group": "neo4j",
        "is_secret": False,
        "placeholder": "neo4j",
        "description": "Database username for authenticating with Neo4j (default: neo4j).",
        "doc_url": f"{DOCS_BASE_URL}#7-neo4j_uri-neo4j_username-neo4j_password--neo4j_database-neo4j-auradb",
    },
    {
        "key": "NEO4J_PASSWORD",
        "label": "Neo4j Password",
        "group": "neo4j",
        "is_secret": True,
        "placeholder": "Your Neo4j instance password",
        "description": "Password generated when creating your Neo4j AuraDB or local database instance.",
        "doc_url": f"{DOCS_BASE_URL}#7-neo4j_uri-neo4j_username-neo4j_password--neo4j_database-neo4j-auradb",
    },
    {
        "key": "NEO4J_DATABASE",
        "label": "Neo4j Database Name",
        "group": "neo4j",
        "is_secret": False,
        "placeholder": "neo4j",
        "description": "Target database name inside your Neo4j instance (default: neo4j).",
        "doc_url": f"{DOCS_BASE_URL}#7-neo4j_uri-neo4j_username-neo4j_password--neo4j_database-neo4j-auradb",
    },
    {
        "key": "TOP_K",
        "label": "Top-K Retrieval Depth",
        "group": "retrieval",
        "is_secret": False,
        "placeholder": "5",
        "description": "Default number of top-scoring chunks returned by vector and hybrid search.",
        "doc_url": f"{DOCS_BASE_URL}#8-top_k-hybrid-retrieval-depth",
    },
]


def _mask_secret(value: str) -> str:
    """
    Create a safe masked preview of a secret or connection URI so users can see
    whether a default is configured without exposing raw credentials.
    """
    if not value:
        return "Not configured"
    if value.startswith(("postgresql://", "postgres://")):
        # Mask password in URI: postgresql://user:****@host/db
        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:••••••••@", value)
    if len(value) <= 8:
        return "••••••••"
    return f"{value[:4]}••••••••{value[-4:]}"


def get_config_value(key: str) -> str:
    """
    Return the active value for `key`. If a non-empty user override exists,
    use it; otherwise automatically fall back to DEFAULT_CONFIG[key].
    """
    override = _runtime_overrides.get(key, "").strip()
    if override:
        return override
    return DEFAULT_CONFIG.get(key, SYSTEM_FALLBACKS.get(key, ""))


def _sync_module_globals() -> None:
    """
    Keep module-level constants synchronized with the active configuration.
    """
    global GOOGLE_API_KEY, AGENT_MODEL, GRAPH_EXTRACTION_MODEL, EMBEDDING_MODEL
    global EMBEDDING_DIMENSIONS, DATABASE_URL, JWT_SECRET_KEY, JWT_EXPIRE_HOURS
    global NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE, TOP_K

    GOOGLE_API_KEY = get_config_value("GOOGLE_API_KEY")
    AGENT_MODEL = get_config_value("AGENT_MODEL") or "gemini-2.5-pro"
    GRAPH_EXTRACTION_MODEL = get_config_value("GRAPH_EXTRACTION_MODEL") or "gemini-2.5-flash"
    EMBEDDING_MODEL = get_config_value("EMBEDDING_MODEL") or "gemini-embedding-001"

    try:
        EMBEDDING_DIMENSIONS = int(get_config_value("EMBEDDING_DIMENSIONS") or "768")
    except ValueError:
        EMBEDDING_DIMENSIONS = 768

    DATABASE_URL = get_config_value("DATABASE_URL")
    JWT_SECRET_KEY = get_config_value("JWT_SECRET_KEY")

    try:
        JWT_EXPIRE_HOURS = max(1, int(get_config_value("JWT_EXPIRE_HOURS") or "168"))
    except ValueError:
        JWT_EXPIRE_HOURS = 168

    NEO4J_URI = get_config_value("NEO4J_URI")
    NEO4J_USERNAME = get_config_value("NEO4J_USERNAME") or "neo4j"
    NEO4J_PASSWORD = get_config_value("NEO4J_PASSWORD")
    NEO4J_DATABASE = get_config_value("NEO4J_DATABASE") or "neo4j"

    try:
        TOP_K = max(1, min(50, int(get_config_value("TOP_K") or "5")))
    except ValueError:
        TOP_K = 5

    # Keep os.environ in sync for libraries such as google-adk that read os.environ["GOOGLE_API_KEY"]
    if GOOGLE_API_KEY:
        os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY


def get_env_settings_payload() -> list[dict[str, Any]]:
    """
    Return all configurable environment variables with their key name,
    secret flag, user-entered custom override (if any), and documentation
    deep-link URL. Default values remain strictly server-side.
    """
    items: list[dict[str, Any]] = []
    for item in ENV_VAR_DEFINITIONS:
        key = item["key"]
        is_secret = item["is_secret"]
        has_custom = bool(_runtime_overrides.get(key, "").strip())

        items.append(
            {
                "key": key,
                "is_secret": is_secret,
                "doc_url": item["doc_url"],
                "source": "custom" if has_custom else "default",
                "custom_value": "" if is_secret else _runtime_overrides.get(key, ""),
            }
        )
    return items


def _persist_overrides_to_dotenv(updates: dict[str, str]) -> None:
    """
    Optionally update the local .env file when requested by the user.
    """
    env_path = Path(__file__).resolve().parent.parent / ".env"
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    updated_keys: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue
        k = stripped.split("=", 1)[0].strip()
        if k in updates:
            val = get_config_value(k)
            new_lines.append(f"{k}={val}")
            updated_keys.add(k)
        else:
            new_lines.append(line)

    for k in updates:
        if k not in updated_keys:
            val = get_config_value(k)
            new_lines.append(f"{k}={val}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def update_runtime_config(
    values: dict[str, str | None],
    persist_to_env: bool = False,
) -> list[dict[str, Any]]:
    """
    Apply user-provided environment variables. Any variable whose value is empty
    or whitespace automatically falls back to DEFAULT_CONFIG[key].
    """
    allowed_keys = {d["key"] for d in ENV_VAR_DEFINITIONS}
    touched: dict[str, str] = {}

    for key, raw_val in values.items():
        if key not in allowed_keys:
            continue
        cleaned = (raw_val or "").strip().replace("\r", "").replace("\n", "")
        if cleaned:
            _runtime_overrides[key] = cleaned
            touched[key] = cleaned
        else:
            # Empty input -> fall back to the default value
            _runtime_overrides.pop(key, None)
            touched[key] = DEFAULT_CONFIG.get(key, "")

    _sync_module_globals()

    if persist_to_env and touched:
        for k in touched:
            DEFAULT_CONFIG[k] = get_config_value(k)
        _persist_overrides_to_dotenv(touched)

    return get_env_settings_payload()


def reset_runtime_config() -> list[dict[str, Any]]:
    """
    Clear all custom overrides and restore every variable to DEFAULT_CONFIG.
    """
    _runtime_overrides.clear()
    _sync_module_globals()
    return get_env_settings_payload()


# Initialize module-level globals on import
GOOGLE_API_KEY: str = ""
AGENT_MODEL: str = "gemini-2.5-pro"
GRAPH_EXTRACTION_MODEL: str = "gemini-2.5-flash"
EMBEDDING_MODEL: str = "gemini-embedding-001"
EMBEDDING_DIMENSIONS: int = 768
DATABASE_URL: str = ""
JWT_SECRET_KEY: str = ""
JWT_EXPIRE_HOURS: int = 168
NEO4J_URI: str = ""
NEO4J_USERNAME: str = "neo4j"
NEO4J_PASSWORD: str = ""
NEO4J_DATABASE: str = "neo4j"
TOP_K: int = 5

_sync_module_globals()
