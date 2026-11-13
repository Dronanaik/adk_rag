"""
Synthetic Golden Dataset generation from the user's indexed Neon pgvector
document chunks and Neo4j Knowledge Graph triples, plus optional LangSmith sync.
"""

import logging
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

import app.config as config
from app.database import get_db_connection
from app.graph_store import get_user_knowledge_graph
from app.tracing import get_langsmith_client

logger = logging.getLogger(__name__)


class EvalExample(BaseModel):
    id: str | None = Field(default=None, description="Optional identifier for the test case.")
    question: str = Field(..., description="A realistic user question grounded in the documents.")
    expected_answer: str = Field(
        default="",
        description="Concise, accurate ground-truth answer supported by the documents.",
    )
    expected_sources: list[str] = Field(
        default_factory=list,
        description="Filenames that contain the evidence for this question.",
    )
    expected_tools: list[str] = Field(
        default_factory=list,
        description=(
            "Expected ADK tools to be used, chosen from: "
            "vector_search, hybrid_search, graph_search, get_entity_relationships."
        ),
    )


class SyntheticEvalDataset(BaseModel):
    examples: list[EvalExample] = Field(default_factory=list)


def _fetch_user_chunks(user_id: str, limit: int = 15) -> list[dict[str, Any]]:
    """Fetch a diverse sample of indexed chunks for `user_id` from Neon pgvector."""
    with get_db_connection(register_pgvector=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT filename, chunk_index, content
                FROM document_chunks
                WHERE user_id = %s
                ORDER BY RANDOM()
                LIMIT %s
                """,
                (user_id, limit),
            )
            rows = cur.fetchall()

    return [
        {
            "filename": row[0],
            "chunk_index": row[1],
            "content": row[2],
        }
        for row in rows
    ]


def _fetch_user_graph_triples(user_id: str, limit: int = 20) -> list[str]:
    """Fetch a sample of Neo4j entity relationships for `user_id`, if available."""
    try:
        kg = get_user_knowledge_graph(user_id)
        links = kg.get("links", [])[:limit]
        triples: list[str] = []
        for link in links:
            src = link.get("source")
            rel = link.get("label") or link.get("type") or "RELATED_TO"
            tgt = link.get("target")
            if src and tgt:
                triples.append(f"{src} -[{rel}]-> {tgt}")
        return triples
    except Exception as exc:
        logger.debug("Skipping Neo4j triples during dataset generation: %s", exc)
        return []


def generate_synthetic_dataset(
    user_id: str,
    num_questions: int = 5,
) -> list[dict[str, Any]]:
    """
    Generate `num_questions` grounded RAG evaluation examples from the user's
    indexed document chunks and Neo4j knowledge graph using Gemini 2.5 Flash.
    """
    num_questions = max(1, min(int(num_questions), 15))
    if not (config.GOOGLE_API_KEY or "").strip():
        raise ValueError("GOOGLE_API_KEY is not configured. Set it in Settings first.")

    chunks = _fetch_user_chunks(user_id=user_id, limit=max(num_questions * 3, 12))
    triples = _fetch_user_graph_triples(user_id=user_id, limit=20)

    if not chunks and not triples:
        raise ValueError(
            "No indexed documents found for this user. Upload at least one document before generating an evaluation dataset."
        )

    chunk_context = "\n\n".join(
        f"[Source: {c['filename']} | Chunk {c['chunk_index']}]\n{c['content'][:900]}"
        for c in chunks
    )
    graph_context = "\n".join(f"- {t}" for t in triples) if triples else "None"

    prompt = f"""You are an expert RAG evaluation dataset designer.
Based ONLY on the Document Chunks and Knowledge Graph Triples below, generate exactly {num_questions} diverse, high-quality evaluation test cases.

Include a mix of:
1. Factual / semantic lookup questions (expected_tools: ["vector_search"] or ["hybrid_search"]).
2. Multi-entity or relationship questions when Knowledge Graph triples are available (expected_tools: ["graph_search"] or ["get_entity_relationships"]).
3. Synthesis questions combining multiple facts (expected_tools: ["hybrid_search", "graph_search"]).

Rules:
- Every `expected_answer` MUST be strictly supported by the provided chunks/triples.
- `expected_sources` MUST list the exact `filename` values from the chunks above (or empty list if purely from graph).
- `expected_tools` MUST only contain valid tool names from: vector_search, hybrid_search, graph_search, get_entity_relationships.

Document Chunks:
{chunk_context}

Knowledge Graph Triples:
{graph_context}
"""

    model_name = (config.GRAPH_EXTRACTION_MODEL or "").strip() or "gemini-2.5-flash"
    client = genai.Client(api_key=config.GOOGLE_API_KEY)
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SyntheticEvalDataset,
            temperature=0.2,
        ),
    )

    parsed = response.parsed
    if not isinstance(parsed, SyntheticEvalDataset):
        if response.text:
            parsed = SyntheticEvalDataset.model_validate_json(response.text)
        else:
            raise RuntimeError("Gemini 2.5 Flash returned an empty dataset response.")

    results: list[dict[str, Any]] = []
    for idx, item in enumerate(parsed.examples[:num_questions], start=1):
        results.append(
            {
                "id": item.id or f"case-{idx}",
                "question": item.question.strip(),
                "expected_answer": item.expected_answer.strip(),
                "expected_sources": [s.strip() for s in item.expected_sources if s.strip()],
                "expected_tools": [t.strip() for t in item.expected_tools if t.strip()],
            }
        )
    return results


def sync_dataset_to_langsmith(
    dataset_name: str,
    examples: list[dict[str, Any]],
    description: str = "Synthetic & curated RAG evaluation dataset for ADK Agentic RAG.",
) -> dict[str, Any]:
    """
    Create or update a LangSmith Dataset with `examples`.
    Returns metadata including `synced`, `dataset_name`, `dataset_id`, and `dataset_url`.
    """
    client = get_langsmith_client()
    if client is None:
        return {
            "synced": False,
            "dataset_name": dataset_name,
            "dataset_id": None,
            "dataset_url": None,
        }

    try:
        try:
            dataset = client.read_dataset(dataset_name=dataset_name)
            # Clear previous examples so the dataset mirrors the current UI list
            existing = list(client.list_examples(dataset_id=dataset.id))
            for ex in existing:
                client.delete_example(ex.id)
        except Exception:
            dataset = client.create_dataset(
                dataset_name=dataset_name,
                description=description,
            )

        inputs = [{"question": ex["question"]} for ex in examples]
        outputs = [
            {
                "expected_answer": ex.get("expected_answer", ""),
                "expected_sources": ex.get("expected_sources", []),
                "expected_tools": ex.get("expected_tools", []),
            }
            for ex in examples
        ]
        if inputs:
            client.create_examples(
                inputs=inputs,
                outputs=outputs,
                dataset_id=dataset.id,
            )

        dataset_url = getattr(dataset, "url", None)
        return {
            "synced": True,
            "dataset_name": dataset_name,
            "dataset_id": str(dataset.id),
            "dataset_url": dataset_url,
        }
    except Exception as exc:
        logger.warning("Failed to sync dataset '%s' to LangSmith: %s", dataset_name, exc)
        return {
            "synced": False,
            "dataset_name": dataset_name,
            "dataset_id": None,
            "dataset_url": None,
            "error": str(exc),
        }
