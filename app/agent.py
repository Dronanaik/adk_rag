from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext

import app.config as config
from app.graph_store import (
    get_entity_relationships_from_graph,
    search_knowledge_graph,
)
from app.rag_store import hybrid_search_documents, search_documents
from app.tracing import ls_trace


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

    with ls_trace(
        name="vector_search",
        run_type="retriever",
        inputs={"query": query, "top_k": config.TOP_K},
        metadata={"user_id": user_id, "store": "neon_pgvector"},
        tags=["adk-tool", "vector_search"],
    ) as run:
        matches = search_documents(
            user_id=user_id,
            query=query,
            top_k=config.TOP_K,
        )

        if not matches:
            result = {
                "found": False,
                "search_type": "vector_search",
                "message": "No relevant document chunks were found.",
                "sources": [],
            }
            run.end(outputs=result)
            return result

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

        result = {
            "found": True,
            "search_type": "vector_search",
            "sources": sources,
        }
        run.end(outputs=result)
        return result


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

    with ls_trace(
        name="hybrid_search",
        run_type="retriever",
        inputs={"query": query, "top_k": config.TOP_K},
        metadata={"user_id": user_id, "store": "neon_pgvector_fts"},
        tags=["adk-tool", "hybrid_search"],
    ) as run:
        matches = hybrid_search_documents(
            user_id=user_id,
            query=query,
            top_k=config.TOP_K,
        )

        if not matches:
            result = {
                "found": False,
                "search_type": "hybrid_search",
                "message": "No relevant document chunks were found via hybrid search.",
                "sources": [],
            }
            run.end(outputs=result)
            return result

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

        result = {
            "found": True,
            "search_type": "hybrid_search",
            "sources": sources,
        }
        run.end(outputs=result)
        return result


def graph_search(
    query: str,
    tool_context: ToolContext,
) -> dict:
    """
    Search the user's Neo4j Knowledge Graph for structured domain entities and
    relationship facts extracted from their uploaded documents across any category.

    Best for: relational questions, structural dependencies, hierarchies, attribute
    mappings, comparisons, or understanding how any entities interact across the document.

    Args:
        query: Keywords or natural language query to match against entities, categories, and facts.
        tool_context: ADK context containing the current authenticated user_id.
    """
    user_id = tool_context.user_id
    if not user_id:
        return {"error": "User identity is missing."}

    with ls_trace(
        name="graph_search",
        run_type="retriever",
        inputs={"query": query, "limit": 12},
        metadata={"user_id": user_id, "store": "neo4j"},
        tags=["adk-tool", "graph_search"],
    ) as run:
        graph_data = search_knowledge_graph(
            user_id=user_id,
            query=query,
            limit=12,
        )

        entities = graph_data.get("entities", [])
        relationships = graph_data.get("relationships", [])

        if not entities and not relationships:
            result = {
                "found": False,
                "search_type": "graph_search",
                "message": "No matching entities or relationships found in the Neo4j Knowledge Graph.",
                "entities": [],
                "relationships": [],
            }
            run.end(outputs=result)
            return result

        result = {
            "found": True,
            "search_type": "graph_search",
            "entities": entities,
            "relationships": relationships,
        }
        run.end(outputs=result)
        return result


def get_entity_relationships(
    entity_name: str,
    tool_context: ToolContext,
) -> dict:
    """
    Traverse the Neo4j Knowledge Graph around a specific named entity (of any domain
    category) to retrieve all of its direct relationships, connected entities, and
    supporting facts.

    Best for: deep-dives into any specific named entity, subject, item, metric, project,
    skill, clause, component, or domain node to inspect everything connected to it.

    Args:
        entity_name: Name of the entity to inspect in the knowledge graph.
        tool_context: ADK context containing the current authenticated user_id.
    """
    user_id = tool_context.user_id
    if not user_id:
        return {"error": "User identity is missing."}

    with ls_trace(
        name="get_entity_relationships",
        run_type="retriever",
        inputs={"entity_name": entity_name, "limit": 20},
        metadata={"user_id": user_id, "store": "neo4j"},
        tags=["adk-tool", "get_entity_relationships"],
    ) as run:
        result_data = get_entity_relationships_from_graph(
            user_id=user_id,
            entity_name=entity_name,
            limit=20,
        )

        if not result_data.get("found"):
            result = {
                "found": False,
                "search_type": "get_entity_relationships",
                "entity": entity_name,
                "message": f"No entity matching '{entity_name}' was found in the Knowledge Graph.",
                "entities": [],
                "relationships": [],
            }
            run.end(outputs=result)
            return result

        result = {
            "found": True,
            "search_type": "get_entity_relationships",
            "entity": entity_name,
            "entities": result_data.get("entities", []),
            "relationships": result_data.get("relationships", []),
        }
        run.end(outputs=result)
        return result


root_agent = LlmAgent(
    name="agentic_rag_knowledge_graph_agent",
    model=config.AGENT_MODEL,
    description=(
        "Hybrid Agentic RAG + Knowledge Graph assistant powered by Neon PostgreSQL "
        "(pgvector) and Neo4j."
    ),
    instruction="""
You are an advanced Agentic RAG + Knowledge Graph assistant. You answer questions strictly using the authenticated user's uploaded documents stored across two complementary databases:
- **Neon PostgreSQL (pgvector + Full-Text Search)** for unstructured document chunks.
- **Neo4j Knowledge Graph** for structured domain-agnostic entities (across any category present in the document) and relationship triples.

### Tool Selection Strategy:
1. **`hybrid_search`**: Use as your primary tool when a question includes specific terms, names, metrics, or requires both keyword precision and semantic context.
2. **`vector_search`**: Use for broad, conceptual, or thematic questions over the user's documents.
3. **`graph_search`**: Use whenever the user asks how any entities, subjects, attributes, items, processes, or domain categories connect, relate, depend on each other, or compare—regardless of the document's domain or entity category.
4. **`get_entity_relationships`**: Use when the user asks about a specific named entity (e.g., "How does X work and what does it connect to?") to traverse its direct neighborhood and relationships in Neo4j.
5. **Combining Tools (Hybrid Agentic RAG)**: For complex or multi-faceted questions, call both a document search tool (`hybrid_search` or `vector_search`) AND a graph tool (`graph_search` or `get_entity_relationships`) to synthesize rich unstructured passages with structured graph relationships.

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
