from google import genai
from google.genai.types import EmbedContentConfig

from app.config import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, GOOGLE_API_KEY

_client: genai.Client | None = None


def get_genai_client() -> genai.Client:
    """
    Lazily initialize and return the Google GenAI client.
    """
    global _client
    if _client is None:
        if not GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY is not configured. Please set it in your .env file."
            )
        _client = genai.Client(api_key=GOOGLE_API_KEY)
    return _client


def embed_text(text: str) -> list[float]:
    """
    Generate a 768-dimensional embedding vector for a single piece of text.
    """
    client = get_genai_client()
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIMENSIONS,
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
            model=EMBEDDING_MODEL,
            contents=batch,
            config=EmbedContentConfig(
                output_dimensionality=EMBEDDING_DIMENSIONS,
            ),
        )
        for emb in response.embeddings:
            all_embeddings.append(list(emb.values))

    return all_embeddings
