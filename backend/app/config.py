"""Environment configuration loader using Pydantic BaseSettings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings loaded exclusively from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    APP_ENV: Literal["development", "staging", "production", "test"] = "development"
    APP_PORT: int = Field(default=8000, ge=1, le=65535)
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173"

    # Database & Storage (Loaded from environment; never hardcoded with live credentials)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/adk_rag"
    DIRECT_DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/adk_rag"
    SUPABASE_URL: str = "http://localhost:54321"
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "documents"

    # Google ADK & Gemini Models
    GOOGLE_API_KEY: str = ""
    GEMINI_FAST_MODEL: str = "gemini-2.5-flash"
    GEMINI_REASONING_MODEL: str = "gemini-2.5-pro"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
    EMBEDDING_DIMENSION: int = Field(default=768, ge=1)

    # Security & Rate Limits (D-05)
    ADMIN_API_KEY: str = ""
    MAX_UPLOAD_SIZE_MB: int = Field(default=20, ge=1, le=100)
    TURN_TIMEOUT_SECONDS: int = Field(default=45, ge=5, le=120)
    TOOL_TIMEOUT_SECONDS: int = Field(default=15, ge=1, le=60)

    # Retrieval & Grounding Thresholds
    DEFAULT_CHUNK_SIZE: int = Field(default=1000, ge=200, le=4000)
    DEFAULT_CHUNK_OVERLAP: int = Field(default=200, ge=0, le=1000)
    RRF_K_CONSTANT: int = Field(default=60, ge=1)
    MIN_SIMILARITY_THRESHOLD: float = Field(default=0.55, ge=0.0, le=1.0)
    MAX_KG_HOPS: int = Field(default=3, ge=1, le=3)
    MAX_KG_SUBGRAPH_NODES: int = Field(default=150, ge=1, le=150)

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS_ALLOWED_ORIGINS into a list of origins."""
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()

