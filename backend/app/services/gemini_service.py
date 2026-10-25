"""Resilient Google Gemini embedding and structured extraction service (AGENTS.md Section 7.3)."""

import asyncio
import hashlib
import math
import re
from collections.abc import Awaitable, Callable
from typing import TypeVar

import structlog
from google import genai
from google.genai import types

from app.config import Settings, get_settings
from app.schemas.common import EntityTypeEnum, RelationTypeEnum
from app.schemas.kg import (
    ChunkKgExtractionResult,
    ExtractedEntityCandidate,
    ExtractedRelationshipCandidate,
)

logger = structlog.get_logger(__name__)

EMBEDDING_BATCH_SIZE: int = 32
RETRY_BACKOFF_SECONDS: tuple[float, float, float] = (1.0, 2.0, 4.0)
TRANSIENT_STATUS_MARKERS: tuple[str, ...] = ("429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE")

_T = TypeVar("_T")

KG_EXTRACTION_SYSTEM_PROMPT: str = (
    "You are a precision Knowledge Graph extraction engine for an enterprise Agentic RAG system. "
    "Extract only concrete, verifiable technical entities and directed relationships explicitly "
    "stated in the provided document chunk. Use canonical singular names for entities and adhere "
    "strictly to the allowed entity_type and relation_type enums."
)


def is_transient_ai_error(exc: BaseException) -> bool:
    """Return True if an exception represents a retryable 429/503/timeout error."""
    if isinstance(exc, TimeoutError):
        return True
    message = str(exc).upper()
    return any(marker in message for marker in TRANSIENT_STATUS_MARKERS)


async def execute_with_resilience(
    operation: Callable[[], Awaitable[_T]],
    *,
    timeout_seconds: float,
    operation_name: str,
    backoff_schedule: tuple[float, ...] = RETRY_BACKOFF_SECONDS,
) -> _T:
    """Execute an async AI operation with timeout and exponential backoff on transient failures."""
    max_attempts = len(backoff_schedule) + 1
    last_error: BaseException | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            async with asyncio.timeout(timeout_seconds):
                return await operation()
        except Exception as exc:
            last_error = exc
            if attempt >= max_attempts or not is_transient_ai_error(exc):
                logger.warning(
                    "gemini_operation_failed",
                    operation=operation_name,
                    attempt=attempt,
                    error=str(exc),
                )
                raise
            delay = backoff_schedule[attempt - 1]
            logger.info(
                "gemini_operation_retrying",
                operation=operation_name,
                attempt=attempt,
                backoff_seconds=delay,
            )
            await asyncio.sleep(delay)

    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Unreachable retry state in {operation_name}")


def generate_deterministic_embedding(text: str, dimension: int = 768) -> list[float]:
    """Generate a deterministic L2-normalized embedding vector from text when offline."""
    normalized_text = text.strip().lower() or "empty"
    raw_values: list[float] = []
    block_index = 0

    while len(raw_values) < dimension:
        digest = hashlib.sha256(f"{normalized_text}:{block_index}".encode()).digest()
        for byte_val in digest:
            if len(raw_values) >= dimension:
                break
            raw_values.append((float(byte_val) / 127.5) - 1.0)
        block_index += 1

    norm = math.sqrt(sum(val * val for val in raw_values)) or 1.0
    return [round(val / norm, 6) for val in raw_values]


def _classify_heuristic_entity_type(name: str) -> EntityTypeEnum:
    """Classify a candidate entity name into the Decision D-03 EntityTypeEnum."""
    lowered = name.lower()
    if any(token in lowered for token in ("service", "api", "gateway", "engine", "system", "db")):
        return EntityTypeEnum.SYSTEM
    if any(token in lowered for token in ("worker", "module", "queue", "cache", "component")):
        return EntityTypeEnum.COMPONENT
    if any(token in lowered for token in ("policy", "rule", "standard", "sla", "compliance")):
        return EntityTypeEnum.POLICY
    if any(token in lowered for token in ("pipeline", "workflow", "process", "ingestion")):
        return EntityTypeEnum.PROCESS
    if any(token in lowered for token in ("team", "org", "group", "department", "council")):
        return EntityTypeEnum.ORGANIZATION
    return EntityTypeEnum.CONCEPT


def _infer_heuristic_relation_type(context_window: str) -> RelationTypeEnum:
    """Infer a Decision D-03 RelationTypeEnum from a local text snippet between two entities."""
    lowered = context_window.lower()
    if any(verb in lowered for verb in ("depends on", "requires", "uses", "calls", "reads from")):
        return RelationTypeEnum.DEPENDS_ON
    if any(verb in lowered for verb in ("part of", "belongs to", "inside", "within")):
        return RelationTypeEnum.PART_OF
    if any(verb in lowered for verb in ("managed by", "owned by", "maintained by")):
        return RelationTypeEnum.MANAGED_BY
    if any(verb in lowered for verb in ("governed by", "enforced by", "regulated by")):
        return RelationTypeEnum.GOVERNED_BY
    if any(verb in lowered for verb in ("communicates with", "streams to", "publishes to")):
        return RelationTypeEnum.COMMUNICATES_WITH
    if any(verb in lowered for verb in ("causes", "triggers", "leads to")):
        return RelationTypeEnum.CAUSES
    if any(verb in lowered for verb in ("mitigates", "prevents", "protects")):
        return RelationTypeEnum.MITIGATES
    return RelationTypeEnum.RELATED_TO


def extract_deterministic_kg(chunk_text: str, document_title: str) -> ChunkKgExtractionResult:
    """Extract deterministic entities and relationships from chunk text when offline."""
    pattern = re.compile(
        r"`([A-Za-z][A-Za-z0-9_\-\s]{2,40})`"
        r"|(\b[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+){0,3}\b)"
    )
    stopwords = {
        "The", "This", "That", "These", "Those", "When", "Where", "While",
        "However", "Therefore", "Furthermore", "Section", "Table", "Figure",
        "Note", "Overview", "Introduction", "Summary", "Step", "Phase",
    }

    entities_by_key: dict[str, ExtractedEntityCandidate] = {}
    ordered_names: list[str] = []

    for match in pattern.finditer(chunk_text):
        raw_name = (match.group(1) or match.group(2) or "").strip()
        if not raw_name or raw_name in stopwords or len(raw_name) < 3:
            continue
        key = raw_name.lower()
        if key not in entities_by_key:
            entities_by_key[key] = ExtractedEntityCandidate(
                canonical_name=raw_name,
                entity_type=_classify_heuristic_entity_type(raw_name),
                description=f"Extracted from '{document_title}'.",
                aliases=[],
            )
            ordered_names.append(raw_name)
        if len(ordered_names) >= 12:
            break

    relationships: list[ExtractedRelationshipCandidate] = []
    for idx in range(len(ordered_names) - 1):
        source_name = ordered_names[idx]
        target_name = ordered_names[idx + 1]
        if source_name.lower() == target_name.lower():
            continue
        relation_type = _infer_heuristic_relation_type(chunk_text)
        relationships.append(
            ExtractedRelationshipCandidate(
                source_entity_name=source_name,
                target_entity_name=target_name,
                relation_type=relation_type,
                confidence=0.85,
                evidence_snippet=chunk_text[:240].strip(),
            )
        )

    return ChunkKgExtractionResult(
        entities=list(entities_by_key.values()),
        relationships=relationships,
    )


class GeminiService:
    """Wrapper around Google GenAI SDK with timeout, backoff, batching, and offline fallback."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._api_key = self._settings.GOOGLE_API_KEY.strip()
        self._client: genai.Client | None = (
            genai.Client(api_key=self._api_key) if self._api_key else None
        )

    @property
    def is_live_configured(self) -> bool:
        """Return True when a live GOOGLE_API_KEY is configured."""
        return self._client is not None

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate 768-dim embeddings in batches of up to 32 texts (ARCHITECTURE.md 3.1)."""
        if not texts:
            return []
        dimension = self._settings.EMBEDDING_DIMENSION
        if self._client is None:
            return [generate_deterministic_embedding(text, dimension) for text in texts]

        all_embeddings: list[list[float]] = []
        for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = texts[start : start + EMBEDDING_BATCH_SIZE]
            batch_vectors = await self._embed_batch_live(batch, dimension)
            all_embeddings.extend(batch_vectors)
        return all_embeddings

    async def embed_query(self, query_text: str) -> list[float]:
        """Generate a single 768-dim embedding vector for a search query."""
        vectors = await self.embed_texts([query_text])
        return vectors[0]

    async def _embed_batch_live(self, batch: list[str], dimension: int) -> list[list[float]]:
        """Call Google GenAI embed_content endpoint with timeout and exponential backoff."""
        client = self._client
        if client is None:
            return [generate_deterministic_embedding(t, dimension) for t in batch]

        async def _call() -> list[list[float]]:
            response = await client.aio.models.embed_content(
                model=self._settings.GEMINI_EMBEDDING_MODEL,
                contents=batch,
                config=types.EmbedContentConfig(output_dimensionality=dimension),
            )
            embeddings = response.embeddings or []
            vectors: list[list[float]] = []
            for item in embeddings:
                values = item.values
                if values is None:
                    raise RuntimeError("Gemini embed_content returned empty vector values.")
                vectors.append([float(v) for v in values])
            if len(vectors) != len(batch):
                raise RuntimeError(
                    f"Expected {len(batch)} embeddings from Gemini, received {len(vectors)}."
                )
            return vectors

        return await execute_with_resilience(
            _call,
            timeout_seconds=float(self._settings.TOOL_TIMEOUT_SECONDS),
            operation_name="gemini_embed_batch",
        )

    async def extract_chunk_kg(
        self,
        chunk_text: str,
        document_title: str,
    ) -> ChunkKgExtractionResult:
        """Extract schema-validated KG entities and relationships from a document chunk."""
        if not chunk_text.strip():
            return ChunkKgExtractionResult(entities=[], relationships=[])
        if self._client is None:
            return extract_deterministic_kg(chunk_text, document_title)

        client = self._client
        prompt = (
            f"Document Title: {document_title}\n\n"
            f"Document Chunk Content:\n{chunk_text}\n\n"
            "Extract all canonical technical entities and directed relationships from this chunk."
        )

        async def _call() -> ChunkKgExtractionResult:
            response = await client.aio.models.generate_content(
                model=self._settings.GEMINI_FAST_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=KG_EXTRACTION_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=ChunkKgExtractionResult,
                    temperature=0.0,
                ),
            )
            raw_json = response.text or "{}"
            return ChunkKgExtractionResult.model_validate_json(raw_json)

        return await execute_with_resilience(
            _call,
            timeout_seconds=float(self._settings.TOOL_TIMEOUT_SECONDS),
            operation_name="gemini_extract_chunk_kg",
        )
