"""Deterministic SHA-256 hashing and entity lookup-key normalization utilities."""

import hashlib
import re

_WHITESPACE_RE = re.compile(r"\s+")
_PUNCTUATION_EDGE_RE = re.compile(r"^[^\w]+|[^\w]+$")


def compute_sha256_bytes(payload: bytes) -> str:
    """Compute lowercase 64-character hexadecimal SHA-256 digest for raw bytes."""
    return hashlib.sha256(payload).hexdigest()


def compute_sha256_text(text: str) -> str:
    """Compute lowercase 64-character hexadecimal SHA-256 digest for UTF-8 text."""
    normalized = text.replace("\r\n", "\n").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def normalize_entity_lookup_key(name: str) -> str:
    """Normalize an entity name into a deterministic lookup key for KG deduplication."""
    collapsed = _WHITESPACE_RE.sub(" ", name.strip()).lower()
    cleaned = _PUNCTUATION_EDGE_RE.sub("", collapsed)
    return cleaned or collapsed

