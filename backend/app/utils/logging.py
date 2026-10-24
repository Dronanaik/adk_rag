"""Structured JSON logging configuration using structlog."""

import logging
from contextvars import ContextVar

import structlog

request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="req_system")


def get_current_request_id() -> str:
    """Return the active request_id bound to the current async context."""
    return request_id_ctx_var.get()


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog for structured JSON output with request context binding."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", level=numeric_level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

