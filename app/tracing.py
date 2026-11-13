"""
LangSmith observability helpers for Google ADK agent & retrieval tools.
Provides a safe, zero-overhead context manager (`ls_trace`) that streams
structured traces to LangSmith when `LANGSMITH_TRACING=true` and
`LANGSMITH_API_KEY` is configured, and acts as a clean no-op otherwise.
"""

from contextlib import contextmanager
import logging
from typing import Any, Iterator

import app.config as config

logger = logging.getLogger(__name__)


class _NoOpRun:
    """Fallback run object when LangSmith tracing is disabled."""

    def end(self, outputs: dict[str, Any] | None = None, error: str | None = None) -> None:
        return None


def is_langsmith_configured() -> bool:
    """Return True when a LangSmith API key is configured."""
    return bool((config.LANGSMITH_API_KEY or "").strip())


def is_tracing_enabled() -> bool:
    """Return True when live LangSmith tracing is enabled and configured."""
    return (
        (config.LANGSMITH_TRACING or "").strip().lower() == "true"
        and is_langsmith_configured()
    )


def get_langsmith_client():
    """Return an initialized `langsmith.Client` or None if unconfigured."""
    if not is_langsmith_configured():
        return None
    try:
        from langsmith import Client

        return Client(
            api_key=config.LANGSMITH_API_KEY,
            api_url=config.LANGSMITH_ENDPOINT or "https://api.smith.langchain.com",
        )
    except Exception:
        logger.exception("Failed to initialize LangSmith client")
        return None


@contextmanager
def ls_trace(
    name: str,
    run_type: str = "chain",
    inputs: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> Iterator[Any]:
    """
    Context manager that opens a LangSmith trace span when live tracing is
    enabled, or yields a `_NoOpRun` without side effects.
    """
    if not is_tracing_enabled():
        yield _NoOpRun()
        return

    client = get_langsmith_client()
    if client is None:
        yield _NoOpRun()
        return

    try:
        from langsmith import trace

        with trace(
            name=name,
            run_type=run_type,
            inputs=inputs or {},
            project_name=config.LANGSMITH_PROJECT or "adk-agentic-rag",
            metadata=metadata or {},
            tags=tags or [],
            client=client,
        ) as run:
            yield run
    except Exception:
        logger.debug("LangSmith trace span '%s' skipped due to tracing error", name, exc_info=True)
        yield _NoOpRun()
