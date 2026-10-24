"""SQLAlchemy 2.0 ORM models package (9-table schema per DATABASE.md)."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base class for all PostgreSQL / pgvector ORM models."""


__all__ = ["Base"]

