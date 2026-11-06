import logging
import re
from typing import Any

from google.genai import types
from pydantic import BaseModel, Field

from app.config import (
    GRAPH_EXTRACTION_MODEL,
    NEO4J_DATABASE,
    NEO4J_PASSWORD,
    NEO4J_URI,
)
from app.database import get_neo4j_driver, init_neo4j_db
from app.embeddings import get_genai_client

logger = logging.getLogger(__name__)

_neo4j_initialized = False


def is_neo4j_configured() -> bool:
    return bool(NEO4J_URI and NEO4J_PASSWORD)


def _ensure_neo4j_schema() -> None:
    global _neo4j_initialized
    if not _neo4j_initialized and is_neo4j_configured():
        init_neo4j_db()
        _neo4j_initialized = True


# ---------------------------------------------------------------------------
# Pydantic Schemas for Gemini Structured Output Entity/Relation Extraction
# ---------------------------------------------------------------------------


class ExtractedEntity(BaseModel):
    name: str = Field(
        description="Canonical name of the entity (e.g., 'Transformer', 'Google', 'Self-Attention')."
    )
    entity_type: str = Field(
        description="Category of entity: Person, Organization, Technology, Concept, Model, Metric, Location, or Event."
    )
    description: str = Field(
        description="Concise 1-sentence summary of what this entity is based on the document."
    )


class ExtractedRelationship(BaseModel):
    source_entity: str = Field(
        description="Exact name of the source entity (must match an extracted entity name)."
    )
    target_entity: str = Field(
        description="Exact name of the target entity (must match an extracted entity name)."
    )
    relation_type: str = Field(
        description="Short UPPER_SNAKE_CASE relationship label (e.g., USES, DEVELOPED_BY, PART_OF, IMPROVES, COMPARED_TO, DEPENDS_ON, AUTHORED_BY)."
    )
    fact: str = Field(
        description="A clear, self-contained factual statement describing how source_entity relates to target_entity."
    )


class KnowledgeGraphExtraction(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relationships: list[ExtractedRelationship] = Field(default_factory=list)


EXTRACTION_PROMPT = """You are an expert Knowledge Graph extraction engine.
Analyze the following text from the document "{filename}" and extract the most important domain entities and relationships.

Guidelines:
1. Extract key entities (People, Organizations, Technologies, Concepts, Models, Metrics, Locations, Events).
2. Normalize entity names consistently (e.g., use "Transformer" instead of both "Transformer" and "the Transformer model").
3. Extract meaningful, factual relationships connecting pairs of extracted entities.
4. Format `relation_type` in UPPER_SNAKE_CASE (e.g., USES, REPLACES, ACHIEVES, PROPOSED_BY, PART_OF, DEPENDS_ON).
5. Each relationship's `fact` must be a concise, factual sentence grounded strictly in the provided text.

Document Excerpt:
---
{text_batch}
---
"""


def _normalize_relation_type(rel: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", rel.strip()).strip("_").upper()
    return cleaned or "RELATES_TO"


def _make_entity_id(user_id: str, entity_name: str) -> str:
    slug = re.sub(r"\s+", " ", entity_name.strip().lower())
    return f"{user_id}::{slug}"


def extract_graph_from_chunks(
    chunks: list[str],
    filename: str,
    max_batches: int = 5,
    batch_char_limit: int = 9000,
) -> KnowledgeGraphExtraction:
    """
    Use Gemini Structured Outputs to extract entities and relationships from document chunks.
    Groups chunks into batches so large documents are processed efficiently.
    """
    if not chunks:
        return KnowledgeGraphExtraction()

    client = get_genai_client()

    # Group chunks into character-bounded batches
    batches: list[str] = []
    current_batch: list[str] = []
    current_len = 0

    for chunk in chunks:
        if current_len + len(chunk) > batch_char_limit and current_batch:
            batches.append("\n\n".join(current_batch))
            current_batch = [chunk]
            current_len = len(chunk)
            if len(batches) >= max_batches:
                break
        else:
            current_batch.append(chunk)
            current_len += len(chunk)

    if current_batch and len(batches) < max_batches:
        batches.append("\n\n".join(current_batch))

    entities_by_key: dict[str, ExtractedEntity] = {}
    relationships_list: list[ExtractedRelationship] = []
    seen_rel_keys: set[tuple[str, str, str]] = set()

    for batch_text in batches:
        try:
            response = client.models.generate_content(
                model=GRAPH_EXTRACTION_MODEL,
                contents=EXTRACTION_PROMPT.format(
                    filename=filename,
                    text_batch=batch_text,
                ),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=KnowledgeGraphExtraction,
                    temperature=0.1,
                ),
            )
            if not response.text:
                continue

            parsed = KnowledgeGraphExtraction.model_validate_json(response.text)

            for ent in parsed.entities:
                name_clean = ent.name.strip()
                if not name_clean or len(name_clean) < 2:
                    continue
                key = name_clean.lower()
                if key not in entities_by_key:
                    entities_by_key[key] = ExtractedEntity(
                        name=name_clean,
                        entity_type=ent.entity_type.strip() or "Concept",
                        description=ent.description.strip(),
                    )

            for rel in parsed.relationships:
                src = rel.source_entity.strip()
                tgt = rel.target_entity.strip()
                if not src or not tgt or src.lower() == tgt.lower():
                    continue

                rel_type = _normalize_relation_type(rel.relation_type)
                rel_key = (src.lower(), rel_type, tgt.lower())
                if rel_key in seen_rel_keys:
                    continue
                seen_rel_keys.add(rel_key)

                # Ensure both endpoint entities exist in entities_by_key
                for endpoint_name in (src, tgt):
                    ep_key = endpoint_name.lower()
                    if ep_key not in entities_by_key:
                        entities_by_key[ep_key] = ExtractedEntity(
                            name=endpoint_name,
                            entity_type="Concept",
                            description=rel.fact.strip(),
                        )

                relationships_list.append(
                    ExtractedRelationship(
                        source_entity=entities_by_key[src.lower()].name,
                        target_entity=entities_by_key[tgt.lower()].name,
                        relation_type=rel_type,
                        fact=rel.fact.strip(),
                    )
                )
        except Exception as exc:
            logger.warning("Knowledge graph batch extraction warning: %s", exc)

    return KnowledgeGraphExtraction(
        entities=list(entities_by_key.values()),
        relationships=relationships_list,
    )


def add_document_to_graph(
    user_id: str,
    document_id: str,
    filename: str,
    chunks: list[str],
) -> dict[str, int]:
    """
    Extract entities & relationships from document chunks and store them in Neo4j.
    Scoped strictly by user_id and linked to document_id.
    """
    if not is_neo4j_configured():
        logger.info("Neo4j is not configured; skipping Knowledge Graph ingestion.")
        return {"entities_extracted": 0, "relationships_extracted": 0}

    _ensure_neo4j_schema()
    extraction = extract_graph_from_chunks(chunks=chunks, filename=filename)

    if not extraction.entities and not extraction.relationships:
        return {"entities_extracted": 0, "relationships_extracted": 0}

    driver = get_neo4j_driver()

    entity_rows = [
        {
            "id": _make_entity_id(user_id, ent.name),
            "name": ent.name,
            "name_lower": ent.name.lower(),
            "entity_type": ent.entity_type,
            "description": ent.description,
        }
        for ent in extraction.entities
    ]

    rel_rows = [
        {
            "source_id": _make_entity_id(user_id, rel.source_entity),
            "target_id": _make_entity_id(user_id, rel.target_entity),
            "relation_type": rel.relation_type,
            "fact": rel.fact,
        }
        for rel in extraction.relationships
    ]

    with driver.session(database=NEO4J_DATABASE) as session:
        # 1. Merge Document node
        session.run(
            """
            MERGE (d:Document {id: $document_id})
            SET d.user_id = $user_id,
                d.filename = $filename,
                d.updated_at = datetime()
            """,
            document_id=str(document_id),
            user_id=user_id,
            filename=filename,
        )

        # 2. Merge Entity nodes and link to Document
        if entity_rows:
            session.run(
                """
                MATCH (d:Document {id: $document_id, user_id: $user_id})
                UNWIND $entities AS ent
                MERGE (e:Entity {id: ent.id})
                ON CREATE SET
                    e.user_id = $user_id,
                    e.name = ent.name,
                    e.name_lower = ent.name_lower,
                    e.entity_type = ent.entity_type,
                    e.description = ent.description,
                    e.created_at = datetime()
                ON MATCH SET
                    e.description = CASE
                        WHEN size(ent.description) > size(coalesce(e.description, ''))
                        THEN ent.description
                        ELSE e.description
                    END,
                    e.entity_type = coalesce(ent.entity_type, e.entity_type)
                MERGE (e)-[:MENTIONED_IN {user_id: $user_id, document_id: $document_id}]->(d)
                """,
                document_id=str(document_id),
                user_id=user_id,
                entities=entity_rows,
            )

        # 3. Merge RELATES_TO edges between Entities
        if rel_rows:
            session.run(
                """
                UNWIND $relationships AS rel
                MATCH (src:Entity {id: rel.source_id, user_id: $user_id})
                MATCH (tgt:Entity {id: rel.target_id, user_id: $user_id})
                MERGE (src)-[r:RELATES_TO {
                    user_id: $user_id,
                    document_id: $document_id,
                    relation_type: rel.relation_type
                }]->(tgt)
                SET r.fact = rel.fact,
                    r.filename = $filename,
                    r.updated_at = datetime()
                """,
                document_id=str(document_id),
                user_id=user_id,
                filename=filename,
                relationships=rel_rows,
            )

    return {
        "entities_extracted": len(entity_rows),
        "relationships_extracted": len(rel_rows),
    }


def delete_document_from_graph(user_id: str, document_id: str) -> dict[str, int]:
    """
    Delete all graph relationships and orphaned entities associated with a document.
    """
    if not is_neo4j_configured():
        return {"deleted_relationships": 0, "deleted_entities": 0}

    _ensure_neo4j_schema()
    driver = get_neo4j_driver()

    with driver.session(database=NEO4J_DATABASE) as session:
        # Delete RELATES_TO relationships from this document
        rel_res = session.run(
            """
            MATCH (:Entity {user_id: $user_id})-[r:RELATES_TO {user_id: $user_id, document_id: $document_id}]->(:Entity {user_id: $user_id})
            DELETE r
            RETURN count(r) AS deleted_rels
            """,
            user_id=user_id,
            document_id=str(document_id),
        ).single()
        deleted_rels = int(rel_res["deleted_rels"]) if rel_res else 0

        # Delete Document node and MENTIONED_IN edges
        session.run(
            """
            MATCH (d:Document {id: $document_id, user_id: $user_id})
            DETACH DELETE d
            """,
            user_id=user_id,
            document_id=str(document_id),
        )

        # Clean up orphaned Entities for this user that have no remaining MENTIONED_IN or RELATES_TO edges
        ent_res = session.run(
            """
            MATCH (e:Entity {user_id: $user_id})
            WHERE NOT (e)-[:MENTIONED_IN]->(:Document)
              AND NOT (e)-[:RELATES_TO]-()
            DELETE e
            RETURN count(e) AS deleted_entities
            """,
            user_id=user_id,
        ).single()
        deleted_entities = int(ent_res["deleted_entities"]) if ent_res else 0

    return {
        "deleted_relationships": deleted_rels,
        "deleted_entities": deleted_entities,
    }


def _extract_search_terms(query: str) -> list[str]:
    stop_words = {
        "what", "how", "why", "when", "where", "who", "which", "are", "is",
        "the", "and", "for", "with", "from", "that", "this", "does", "about",
        "tell", "me", "in", "of", "to", "a", "an", "on", "by", "between",
    }
    words = re.findall(r"[A-Za-z0-9_\-]+", query.lower())
    terms = [w for w in words if len(w) >= 3 and w not in stop_words]
    if not terms and query.strip():
        terms = [query.strip().lower()]
    return terms[:8]


def search_knowledge_graph(
    user_id: str,
    query: str,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Search the user's Neo4j Knowledge Graph for entities and relationship facts
    matching the query.
    """
    if not is_neo4j_configured():
        return {"entities": [], "relationships": []}

    _ensure_neo4j_schema()
    terms = _extract_search_terms(query)
    full_query = query.strip().lower()

    driver = get_neo4j_driver()
    with driver.session(database=NEO4J_DATABASE) as session:
        # 1. Search matching relationships and connected entities
        rel_records = session.run(
            """
            MATCH (src:Entity {user_id: $user_id})-[r:RELATES_TO {user_id: $user_id}]->(tgt:Entity {user_id: $user_id})
            WHERE toLower(src.name) CONTAINS $full_query
               OR toLower(tgt.name) CONTAINS $full_query
               OR toLower(coalesce(r.fact, '')) CONTAINS $full_query
               OR ANY(term IN $terms WHERE
                    src.name_lower CONTAINS term
                    OR tgt.name_lower CONTAINS term
                    OR toLower(coalesce(r.fact, '')) CONTAINS term
                    OR toLower(r.relation_type) CONTAINS term
               )
            RETURN
                src.name AS source,
                src.entity_type AS source_type,
                r.relation_type AS relation_type,
                tgt.name AS target,
                tgt.entity_type AS target_type,
                r.fact AS fact,
                r.filename AS filename,
                r.document_id AS document_id
            LIMIT $limit
            """,
            user_id=user_id,
            full_query=full_query,
            terms=terms,
            limit=limit,
        ).data()

        # 2. Search matching entities
        ent_records = session.run(
            """
            MATCH (e:Entity {user_id: $user_id})
            WHERE e.name_lower CONTAINS $full_query
               OR toLower(coalesce(e.description, '')) CONTAINS $full_query
               OR ANY(term IN $terms WHERE
                    e.name_lower CONTAINS term
                    OR toLower(coalesce(e.description, '')) CONTAINS term
               )
            RETURN
                e.name AS name,
                e.entity_type AS entity_type,
                e.description AS description
            LIMIT $limit
            """,
            user_id=user_id,
            full_query=full_query,
            terms=terms,
            limit=limit,
        ).data()

    return {
        "entities": ent_records,
        "relationships": rel_records,
    }


def get_entity_relationships_from_graph(
    user_id: str,
    entity_name: str,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Traverse the Neo4j Knowledge Graph around a specific entity (direct + 2-hop connections).
    Inspired by get_entity_relationships in agentic-rag-knowledge-graph.
    """
    if not is_neo4j_configured():
        return {"entity": entity_name, "found": False, "relationships": [], "related_entities": []}

    _ensure_neo4j_schema()
    target_lower = entity_name.strip().lower()
    driver = get_neo4j_driver()

    with driver.session(database=NEO4J_DATABASE) as session:
        # Match primary entity or entities matching the name
        entity_matches = session.run(
            """
            MATCH (e:Entity {user_id: $user_id})
            WHERE e.name_lower CONTAINS $target_lower
               OR $target_lower CONTAINS e.name_lower
            RETURN e.name AS name, e.entity_type AS entity_type, e.description AS description
            LIMIT 5
            """,
            user_id=user_id,
            target_lower=target_lower,
        ).data()

        if not entity_matches:
            return {
                "entity": entity_name,
                "found": False,
                "entities": [],
                "relationships": [],
            }

        # Traverse 1-hop and 2-hop relationships around matched entities
        rel_records = session.run(
            """
            MATCH (e:Entity {user_id: $user_id})
            WHERE e.name_lower CONTAINS $target_lower
               OR $target_lower CONTAINS e.name_lower
            MATCH (e)-[r:RELATES_TO {user_id: $user_id}]-(neighbor:Entity {user_id: $user_id})
            RETURN DISTINCT
                startNode(r).name AS source,
                startNode(r).entity_type AS source_type,
                r.relation_type AS relation_type,
                endNode(r).name AS target,
                endNode(r).entity_type AS target_type,
                r.fact AS fact,
                r.filename AS filename
            LIMIT $limit
            """,
            user_id=user_id,
            target_lower=target_lower,
            limit=limit,
        ).data()

    return {
        "entity": entity_name,
        "found": True,
        "entities": entity_matches,
        "relationships": rel_records,
    }


def get_user_knowledge_graph(
    user_id: str,
    limit_nodes: int = 80,
    limit_edges: int = 120,
) -> dict[str, Any]:
    """
    Return the user's Knowledge Graph nodes and edges for interactive UI visualization.
    """
    if not is_neo4j_configured():
        return {"configured": False, "nodes": [], "edges": [], "stats": {"entities": 0, "relationships": 0}}

    _ensure_neo4j_schema()
    driver = get_neo4j_driver()

    with driver.session(database=NEO4J_DATABASE) as session:
        nodes = session.run(
            """
            MATCH (e:Entity {user_id: $user_id})
            OPTIONAL MATCH (e)-[r:RELATES_TO {user_id: $user_id}]-()
            WITH e, count(r) AS degree
            ORDER BY degree DESC, e.name ASC
            LIMIT $limit_nodes
            RETURN
                e.id AS id,
                e.name AS name,
                coalesce(e.entity_type, 'Concept') AS entity_type,
                coalesce(e.description, '') AS description,
                degree
            """,
            user_id=user_id,
            limit_nodes=limit_nodes,
        ).data()

        edges = session.run(
            """
            MATCH (src:Entity {user_id: $user_id})-[r:RELATES_TO {user_id: $user_id}]->(tgt:Entity {user_id: $user_id})
            RETURN
                src.id AS source_id,
                src.name AS source,
                tgt.id AS target_id,
                tgt.name AS target,
                r.relation_type AS relation_type,
                coalesce(r.fact, '') AS fact,
                coalesce(r.filename, '') AS filename,
                coalesce(r.document_id, '') AS document_id
            LIMIT $limit_edges
            """,
            user_id=user_id,
            limit_edges=limit_edges,
        ).data()

        counts = session.run(
            """
            MATCH (e:Entity {user_id: $user_id})
            WITH count(e) AS total_entities
            OPTIONAL MATCH (:Entity {user_id: $user_id})-[r:RELATES_TO {user_id: $user_id}]->(:Entity {user_id: $user_id})
            RETURN total_entities, count(r) AS total_relationships
            """,
            user_id=user_id,
        ).single()

    total_entities = int(counts["total_entities"]) if counts else len(nodes)
    total_relationships = int(counts["total_relationships"]) if counts else len(edges)

    return {
        "configured": True,
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "entities": total_entities,
            "relationships": total_relationships,
        },
    }


def get_graph_stats() -> dict[str, Any]:
    """
    Return global Neo4j entity and relationship counts for the /ingest/status endpoint.
    """
    if not is_neo4j_configured():
        return {"status": "unconfigured", "total_entities": 0, "total_relationships": 0}

    _ensure_neo4j_schema()
    driver = get_neo4j_driver()
    with driver.session(database=NEO4J_DATABASE) as session:
        ent_rec = session.run("MATCH (e:Entity) RETURN count(e) AS cnt").single()
        rel_rec = session.run("MATCH ()-[r:RELATES_TO]->() RETURN count(r) AS cnt").single()

    return {
        "status": "ready",
        "total_entities": int(ent_rec["cnt"]) if ent_rec else 0,
        "total_relationships": int(rel_rec["cnt"]) if rel_rec else 0,
    }
