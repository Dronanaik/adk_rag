from google import genai
from google.genai.types import EmbedContentConfig

import app.config as config

_client: genai.Client | None = None
_client_api_key: str = ""


def reset_genai_client() -> None:
    """Reset the cached Google GenAI client so updated API keys take effect immediately."""
    global _client, _client_api_key
    _client = None
    _client_api_key = ""


def get_genai_client() -> genai.Client:
    """
    Lazily initialize and return the Google GenAI client.
    Automatically re-initializes if GOOGLE_API_KEY was updated at runtime.
    """
    global _client, _client_api_key
    active_key = config.GOOGLE_API_KEY
    if _client is None or _client_api_key != active_key:
        if not active_key:
            raise ValueError(
                "GOOGLE_API_KEY is not configured. Please set it in Settings or your .env file."
            )
        _client = genai.Client(api_key=active_key)
        _client_api_key = active_key
    return _client


def embed_text(text: str) -> list[float]:
    """
    Generate a 768-dimensional embedding vector for a single piece of text.
    """
    client = get_genai_client()
    response = client.models.embed_content(
        model=config.EMBEDDING_MODEL,
        contents=text,
        config=EmbedContentConfig(
            output_dimensionality=config.EMBEDDING_DIMENSIONS,
        ),
    )
    return list(response.embeddings[0].values)


def embed_texts(texts: list[str], batch_size: int = 50) -> list[list[float]]:
    """
    Generate embeddings for multiple text chunks in batches for high throughput.
    """
    if not texts:
        return []

    client = get_genai_client()
    all_embeddings: list[list[float]] = []

    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        response = client.models.embed_content(
            model=config.EMBEDDING_MODEL,
            contents=batch,
            config=EmbedContentConfig(
                output_dimensionality=config.EMBEDDING_DIMENSIONS,
            ),
        )
        for emb in response.embeddings:
            all_embeddings.append(list(emb.values))

    return all_embeddings
