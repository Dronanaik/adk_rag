from google import genai
from google.genai.types import EmbedContentConfig

from app.config import GOOGLE_API_KEY

client = genai.Client(api_key=GOOGLE_API_KEY)

EMBEDDING_MODEL = "gemini-embedding-001"

def embed_text(text: str) -> list[float]:
    """
    Generate an embedding for one piece of text.
    """

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=EmbedContentConfig(
            output_dimensionality=768,
        ),
    )

    return response.embeddings[0].values

def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for multiple texts.
    """

    embeddings = []

    for text in texts:
        embeddings.append(embed_text(text))

    return embeddings
