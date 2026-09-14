"""Database layer — SQLAlchemy 2.0 models shared by CLI and API.

Schema: docs/DATABASE.md. Local dev uses SQLite; prod uses Neon Postgres
via DATABASE_URL. Models land in dataforge/db/models.py (next step).
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all DataForge ORM models."""


__all__ = ["Base"]
