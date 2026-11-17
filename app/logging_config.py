"""
Centralized structured logging, context correlation, secret redaction,
and rotating JSONL persistence for ADK Agentic RAG + Knowledge Graph.
"""

from __future__ import annotations

from collections import deque
from contextlib import contextmanager
import contextvars
from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re
import sys
import traceback
from typing import Any, Iterator

# ContextVars propagated across async tasks and asyncio.to_thread() workers
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_id", default="-")
session_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("session_id", default="-")
channel_var: contextvars.ContextVar[str] = contextvars.ContextVar("channel", default="app")

_LOG_SETUP_DONE = False
_ACTIVE_LOG_DIR: Path = Path("logs")

_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(Bearer\s+)[A-Za-z0-9\-_\.]+", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"([?&](?:token|api_key|key)=)[^&\s]+", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"(postgres(?:ql)?://[^:\s]+:)[^@\s]+(@)", re.IGNORECASE), r"\1[REDACTED]\2"),
    (re.compile(r"(neo4j(?:\+s)?://[^:\s]+:)[^@\s]+(@)", re.IGNORECASE), r"\1[REDACTED]\2"),
    (re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b"), "[REDACTED_GOOGLE_KEY]"),
    (re.compile(r"\blsv2_[A-Za-z0-9_]{16,}\b"), "[REDACTED_LANGSMITH_KEY]"),
]


def redact_secrets(text: str) -> str:
    """Mask bearer tokens, API keys, and DB URI passwords in log strings."""
    if not text:
        return text
    cleaned = str(text).replace("\r", "")
    for pattern, replacement in _SECRET_PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned


@contextmanager
def bind_log_context(
    *,
    request_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    channel: str | None = None,
) -> Iterator[None]:
    """Temporarily bind correlation metadata to the current async/thread context."""
    tokens: list[tuple[contextvars.ContextVar[str], contextvars.Token[str]]] = []
    if request_id is not None:
        tokens.append((request_id_var, request_id_var.set(str(request_id))))
    if user_id is not None:
        tokens.append((user_id_var, user_id_var.set(str(user_id))))
    if session_id is not None:
        tokens.append((session_id_var, session_id_var.set(str(session_id))))
    if channel is not None:
        tokens.append((channel_var, channel_var.set(str(channel))))
    try:
        yield
    finally:
        for var, tok in reversed(tokens):
            var.reset(tok)


class ContextCorrelationFilter(logging.Filter):
    """Inject correlation IDs and redact secrets on every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_var.get()
        if not hasattr(record, "user_id"):
            record.user_id = user_id_var.get()
        if not hasattr(record, "session_id"):
            record.session_id = session_id_var.get()
        if not hasattr(record, "channel"):
            record.channel = channel_var.get()
        if not hasattr(record, "duration_ms"):
            record.duration_ms = None
        return True


class JsonLinesFormatter(logging.Formatter):
    """Emit one structured JSON object per log line for easy grepping and UI tailing."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        msg = redact_secrets(record.getMessage())
        payload: dict[str, Any] = {
            "timestamp": ts,
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
            "channel": getattr(record, "channel", "-"),
            "request_id": getattr(record, "request_id", "-"),
            "user_id": getattr(record, "user_id", "-"),
            "session_id": getattr(record, "session_id", "-"),
            "message": msg,
        }
        duration_ms = getattr(record, "duration_ms", None)
        if duration_ms is not None:
            payload["duration_ms"] = round(float(duration_ms), 2)
        extra_data = getattr(record, "extra_data", None)
        if isinstance(extra_data, dict) and extra_data:
            payload["data"] = {
                k: redact_secrets(v) if isinstance(v, str) else v
                for k, v in extra_data.items()
            }
        if record.exc_info:
            tb = "".join(traceback.format_exception(*record.exc_info))
            payload["exception"] = redact_secrets(tb)
        elif record.exc_text:
            payload["exception"] = redact_secrets(record.exc_text)
        return json.dumps(payload, ensure_ascii=False)


class ReadableConsoleFormatter(logging.Formatter):
    """Compact human-readable console format with correlation context."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]
        req_id = getattr(record, "request_id", "-")
        user_id = getattr(record, "user_id", "-")
        channel = getattr(record, "channel", "app")
        dur = getattr(record, "duration_ms", None)
        dur_str = f" ({dur:.1f}ms)" if dur is not None else ""
        msg = redact_secrets(record.getMessage())
        line = (
            f"{ts} | {record.levelname:<7} | {channel} "
            f"[req={req_id} user={user_id}] | "
            f"{record.name}:{record.lineno} | {msg}{dur_str}"
        )
        if record.exc_info:
            tb = "".join(traceback.format_exception(*record.exc_info))
            line = f"{line}\n{redact_secrets(tb)}"
        return line


def setup_logging(
    *,
    log_level: str = "INFO",
    log_dir: str = "logs",
    log_to_file: bool = True,
    force: bool = False,
) -> Path:
    """Configure root logging with console + rotating JSONL handlers (`app.jsonl`, `errors.jsonl`)."""
    global _LOG_SETUP_DONE, _ACTIVE_LOG_DIR
    if _LOG_SETUP_DONE and not force:
        return _ACTIVE_LOG_DIR

    level = getattr(logging, (log_level or "INFO").upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    # Clear duplicate handlers on reload/force
    for h in list(root.handlers):
        root.removeHandler(h)

    corr_filter = ContextCorrelationFilter()

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(ReadableConsoleFormatter())
    console.addFilter(corr_filter)
    root.addHandler(console)

    target_dir = Path(log_dir or "logs")
    _ACTIVE_LOG_DIR = target_dir

    if log_to_file:
        target_dir.mkdir(parents=True, exist_ok=True)
        json_fmt = JsonLinesFormatter()

        app_handler = RotatingFileHandler(
            target_dir / "app.jsonl",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        app_handler.setLevel(level)
        app_handler.setFormatter(json_fmt)
        app_handler.addFilter(corr_filter)
        root.addHandler(app_handler)

        err_handler = RotatingFileHandler(
            target_dir / "errors.jsonl",
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        err_handler.setLevel(logging.ERROR)
        err_handler.setFormatter(json_fmt)
        err_handler.addFilter(corr_filter)
        root.addHandler(err_handler)

    # Reduce third-party noise while preserving warnings/errors
    for noisy in ("httpx", "httpcore", "urllib3", "asyncio", "neo4j.notifications"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _LOG_SETUP_DONE = True
    return target_dir


def read_recent_logs(
    *,
    level: str | None = None,
    request_id: str | None = None,
    channel: str | None = None,
    limit: int = 100,
    errors_only: bool = False,
) -> list[dict[str, Any]]:
    """Read and filter recent structured JSONL log entries from disk."""
    filename = "errors.jsonl" if errors_only or (level or "").upper() == "ERROR" else "app.jsonl"
    path = _ACTIVE_LOG_DIR / filename
    if not path.exists():
        return []

    max_rows = max(1, min(int(limit or 100), 500))
    # Tail up to 2000 raw lines to keep reads fast
    buf: deque[str] = deque(maxlen=2000)
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for raw_line in f:
            if raw_line.strip():
                buf.append(raw_line)

    want_level = level.upper() if level else None
    results: list[dict[str, Any]] = []
    for raw in reversed(buf):
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if want_level and entry.get("level") != want_level:
            continue
        if request_id and entry.get("request_id") != request_id:
            continue
        if channel and entry.get("channel") != channel:
            continue
        results.append(entry)
        if len(results) >= max_rows:
            break
    return results
