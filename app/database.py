import logging
import re
from contextlib import contextmanager
from typing import Generator

import psycopg2
from psycopg2 import pool
from pgvector.psycopg2 import register_vector
from neo4j import Driver, GraphDatabase, NotificationMinimumSeverity

import app.config as config
from app.config import EMBEDDING_DIMENSIONS

logger = logging.getLogger(__name__)
logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)

_pg_pool: pool.ThreadedConnectionPool | None = None
_neo4j_driver: Driver | None = None


def _normalize_database_url(url: str) -> str:
    """
    Normalize Neon PostgreSQL connection string and auto-fix common copy-paste typos
    (such as missing '?' before 'sslmode=require').
    """
    cleaned = url.strip().strip("'").strip('"')
    if "?" not in cleaned and "sslmode=" in cleaned:
        cleaned = re.sub(r"(?<!\?)sslmode=", "?sslmode=", cleaned, count=1)
    return cleaned


SCHEMA_SQL = f"""
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_users_email
    ON users (LOWER(email));

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    entity_count INTEGER NOT NULL DEFAULT 0,
    relationship_count INTEGER NOT NULL DEFAULT 0,
    character_count INTEGER NOT NULL DEFAULT 0,
    metadata JSONB DEFAULT '{{}}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR({EMBEDDING_DIMENSIONS}) NOT NULL,
    metadata JSONB DEFAULT '{{}}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_user_id
    ON documents (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_document_chunks_user_doc
    ON document_chunks (user_id, document_id);

CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw
    ON document_chunks
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_document_chunks_content_fts
    ON document_chunks
    USING gin (to_tsvector('english', content));
"""


def _get_pg_pool() -> pool.ThreadedConnectionPool:
    """
    Lazily initialize the Neon PostgreSQL connection pool.
    Configured with TCP keepalives to handle Neon serverless scaling smoothly.
    """
    global _pg_pool
    if _pg_pool is None:
        if not config.DATABASE_URL:
            raise ValueError(
                "DATABASE_URL is not configured. Please set your Neon PostgreSQL connection string in .env."
            )
        dsn = _normalize_database_url(config.DATABASE_URL)
        _pg_pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=dsn,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
        )
    return _pg_pool


@contextmanager
def get_db_connection(register_pgvector: bool = True) -> Generator:
    """
    Yield a validated PostgreSQL connection from the pool.
    Automatically reconnects if Neon closed an idle serverless connection.
    """
    pg_pool = _get_pg_pool()
    conn = pg_pool.getconn()
    try:
        # Validate connection is alive (Neon serverless may close idle connections)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            try:
                pg_pool.putconn(conn, close=True)
            except Exception as close_err:
                logger.debug("Ignored error returning stale connection: %s", close_err)
            conn = psycopg2.connect(
                dsn=_normalize_database_url(config.DATABASE_URL),
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5,
            )

        if register_pgvector:
            register_vector(conn)

        yield conn
        conn.commit()
    except Exception:
        if conn and not conn.closed:
            conn.rollback()
        raise
    finally:
        if conn:
            try:
                pg_pool.putconn(conn, close=conn.closed != 0)
            except Exception as pool_err:
                logger.debug("Ignored error returning connection to pool: %s", pool_err)


def init_postgres_db() -> None:
    """
    Enable pgvector extension and create tables & indexes in Neon PostgreSQL.
    """
    with get_db_connection(register_pgvector=False) as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
        conn.commit()
    logger.info("Neon PostgreSQL (pgvector) schema initialized successfully.")


def get_neo4j_driver() -> Driver:
    """
    Lazily initialize and return the Neo4j driver.
    Suppresses benign GQL notifications when querying empty labels/relationship types.
    """
    global _neo4j_driver
    if _neo4j_driver is None:
        if not config.NEO4J_URI or not config.NEO4J_PASSWORD:
            raise ValueError(
                "NEO4J_URI and NEO4J_PASSWORD must be configured in your .env file."
            )
        _neo4j_driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD),
            notifications_min_severity=NotificationMinimumSeverity.OFF,
            warn_notification_severity=NotificationMinimumSeverity.OFF,
        )
    return _neo4j_driver


def init_neo4j_db() -> None:
    """
    Initialize Neo4j constraints and indexes for fast entity and document lookup.
    """
    driver = get_neo4j_driver()
    queries = [
        "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
        "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
        "CREATE INDEX entity_user_idx IF NOT EXISTS FOR (e:Entity) ON (e.user_id)",
        "CREATE INDEX entity_name_idx IF NOT EXISTS FOR (e:Entity) ON (e.name_lower)",
        "CREATE INDEX document_user_idx IF NOT EXISTS FOR (d:Document) ON (d.user_id)",
    ]
    with driver.session(database=config.NEO4J_DATABASE) as session:
        for query in queries:
            session.run(query)
    logger.info("Neo4j Knowledge Graph constraints and indexes initialized successfully.")


def init_all_databases() -> dict[str, str]:
    """
    Initialize both Neon PostgreSQL and Neo4j schemas safely on startup.
    Returns status strings for both stores.
    """
    status = {"postgres": "unconfigured", "neo4j": "unconfigured"}

    if config.DATABASE_URL:
        try:
            init_postgres_db()
            status["postgres"] = "ready"
        except Exception:
            logger.warning("Neon PostgreSQL initialization warning", exc_info=True)
            status["postgres"] = "error"

    if config.NEO4J_URI and config.NEO4J_PASSWORD:
        try:
            init_neo4j_db()
            status["neo4j"] = "ready"
        except Exception:
            logger.warning("Neo4j initialization warning", exc_info=True)
            status["neo4j"] = "error"

    return status


def reload_database_connections() -> dict[str, str]:
    """
    Close existing PostgreSQL pool and Neo4j driver and re-initialize
    connections with the latest active configuration.
    """
    close_all_databases()
    return init_all_databases()


def close_all_databases() -> None:
    """
    Cleanly close PostgreSQL pool and Neo4j driver on shutdown.
    """
    global _pg_pool, _neo4j_driver
    if _pg_pool is not None:
        try:
            _pg_pool.closeall()
        except Exception as pg_err:
            logger.debug("Ignored error closing PostgreSQL pool: %s", pg_err)
        _pg_pool = None

    if _neo4j_driver is not None:
        try:
            _neo4j_driver.close()
        except Exception as neo_err:
            logger.debug("Ignored error closing Neo4j driver: %s", neo_err)
        _neo4j_driver = None
