from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext

from app.config import AGENT_MODEL, TOP_K
from app.graph_store import (
    get_entity_relationships_from_graph,
    search_knowledge_graph,
)
from app.rag_store import hybrid_search_documents, search_documents


def vector_search(
    query: str,
    tool_context: ToolContext,
) -> dict:
    """
    Perform pure semantic vector similarity search over the user's document chunks
    stored in Neon PostgreSQL (pgvector).

    Best for: conceptual, thematic, or broad open-ended questions.

    Args:
        query: A natural language search query describing the information needed.
        tool_context: ADK context containing the current authenticated user_id.
    """
    user_id = tool_context.user_id
    if not user_id:
        return {"error": "User identity is missing."}

    matches = search_documents(
        user_id=user_id,
        query=query,
        top_k=TOP_K,
    )

    if not matches:
        return {
            "found": False,
            "search_type": "vector_search",
            "message": "No relevant document chunks were found.",
            "sources": [],
        }

    sources = []
    for index, match in enumerate(matches, start=1):
        metadata = match["metadata"]
        sources.append(
            {
                "source_number": index,
                "filename": metadata.get("filename"),
                "document_id": metadata.get("document_id"),
                "chunk_index": metadata.get("chunk_index"),
                "similarity": match.get("similarity"),
                "distance": match.get("distance"),
                "text": match["text"],
            }
        )

    return {
        "found": True,
        "search_type": "vector_search",
        "sources": sources,
    }


def hybrid_search(
    query: str,
    tool_context: ToolContext,
) -> dict:
    """
    Perform hybrid retrieval combining pgvector semantic similarity with PostgreSQL
    Full-Text Search (tsvector / keyword ranking) in Neon PostgreSQL.

    Best for: queries containing specific technical terms, acronyms, names, numbers,
    or exact phrases alongside conceptual meaning.

    Args:
        query: Search query containing keywords and conceptual terms.
        tool_context: ADK context containing the current authenticated user_id.
    """
    user_id = tool_context.user_id
    if not user_id:
        return {"error": "User identity is missing."}

    matches = hybrid_search_documents(
        user_id=user_id,
        query=query,
        top_k=TOP_K,
    )

    if not matches:
        return {
            "found": False,
            "search_type": "hybrid_search",
            "message": "No relevant document chunks were found via hybrid search.",
            "sources": [],
        }

    sources = []
    for index, match in enumerate(matches, start=1):
        metadata = match["metadata"]
        sources.append(
            {
                "source_number": index,
                "filename": metadata.get("filename"),
                "document_id": metadata.get("document_id"),
                "chunk_index": metadata.get("chunk_index"),
                "combined_score": match.get("combined_score"),
                "vector_similarity": match.get("vector_similarity"),
                "keyword_score": match.get("keyword_score"),
                "text": match["text"],
            }
        )

    return {
        "found": True,
        "search_type": "hybrid_search",
        "sources": sources,
    }


def graph_search(
    query: str,
    tool_context: ToolContext,
) -> dict:
    """
    Search the user's Neo4j Knowledge Graph for structured entities and relationship
    facts extracted from their uploaded documents.

    Best for: relational questions, architecture/system connections, comparing concepts,
    or understanding how multiple entities interact.

    Args:
        query: Keywords or natural language query to match against entities and facts.
        tool_context: ADK context containing the current authenticated user_id.
    """
    user_id = tool_context.user_id
    if not user_id:
        return {"error": "User identity is missing."}

    graph_data = search_knowledge_graph(
        user_id=user_id,
        query=query,
        limit=12,
    )

    entities = graph_data.get("entities", [])
    relationships = graph_data.get("relationships", [])

    if not entities and not relationships:
        return {
            "found": False,
            "search_type": "graph_search",
            "message": "No matching entities or relationships found in the Neo4j Knowledge Graph.",
            "entities": [],
            "relationships": [],
        }

    return {
        "found": True,
        "search_type": "graph_search",
        "entities": entities,
        "relationships": relationships,
    }


def get_entity_relationships(
    entity_name: str,
    tool_context: ToolContext,
) -> dict:
    """
    Traverse the Neo4j Knowledge Graph around a specific named entity to retrieve all
    of its direct relationships, connected entities, and supporting facts.

    Best for: deep-dives into a specific concept, person, organization, model, or
    component (e.g., 'Transformer', 'Self-Attention', 'BLEU').

    Args:
        entity_name: Name of the entity to inspect in the knowledge graph.
        tool_context: ADK context containing the current authenticated user_id.
    """
    user_id = tool_context.user_id
    if not user_id:
        return {"error": "User identity is missing."}

    result = get_entity_relationships_from_graph(
        user_id=user_id,
        entity_name=entity_name,
        limit=20,
    )

    if not result.get("found"):
        return {
            "found": False,
            "search_type": "get_entity_relationships",
            "entity": entity_name,
            "message": f"No entity matching '{entity_name}' was found in the Knowledge Graph.",
            "entities": [],
            "relationships": [],
        }

    return {
        "found": True,
        "search_type": "get_entity_relationships",
        "entity": entity_name,
        "entities": result.get("entities", []),
        "relationships": result.get("relationships", []),
    }


root_agent = LlmAgent(
    name="agentic_rag_knowledge_graph_agent",
    model=AGENT_MODEL,
    description=(
        "Hybrid Agentic RAG + Knowledge Graph assistant powered by Neon PostgreSQL "
        "(pgvector) and Neo4j."
    ),
    instruction="""
You are an advanced Agentic RAG + Knowledge Graph assistant. You answer questions strictly using the authenticated user's uploaded documents stored across two complementary databases:
- **Neon PostgreSQL (pgvector + Full-Text Search)** for unstructured document chunks.
- **Neo4j Knowledge Graph** for structured entities and relationship triples.

### Tool Selection Strategy:
1. **`hybrid_search`**: Use as your primary tool when a question includes specific terms, names, metrics, or requires both keyword precision and semantic context.
2. **`vector_search`**: Use for broad, conceptual, or thematic questions over the user's documents.
3. **`graph_search`**: Use when the user asks how concepts, technologies, people, or organizations connect, relate, or compare.
4. **`get_entity_relationships`**: Use when the user asks about a specific entity (e.g., "How does X work and what does it connect to?") to traverse its direct relationships in Neo4j.
5. **Combining Tools (Hybrid Agentic RAG)**: For complex questions, call both a document search tool (`hybrid_search` or `vector_search`) AND a graph tool (`graph_search` or `get_entity_relationships`) to synthesize rich unstructured passages with structured graph relationships.

### Grounding & Citation Rules:
1. Answer ONLY using facts present in the retrieved chunks and knowledge graph triples. Do not invent facts.
2. If neither the vector store nor the knowledge graph contains the answer, clearly state:
   "I could not find that information in the uploaded documents or knowledge graph."
3. Cite document chunks using:
   `[Source: filename, chunk N]`
4. When using facts from the Neo4j Knowledge Graph, also include relationship citations using:
   `[Graph: Source -> RELATION_TYPE -> Target]`
5. Never reveal or reference data belonging to another user.
""",
    tools=[
        hybrid_search,
        vector_search,
        graph_search,
        get_entity_relationships,
    ],
)
