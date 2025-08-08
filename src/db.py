from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Determine project and data directories relative to this file for portability
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)

_DB_PATH = _DATA_DIR / "transactions.db"
_SQLITE_URL = f"sqlite:///{_DB_PATH.as_posix()}"

# Create engine and session factory
engine = create_engine(
    _SQLITE_URL,
    future=True,
    echo=False,  # set to True for SQL echo during debugging
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Declarative base for ORM models
Base = declarative_base()


def get_db_path() -> str:
    return str(_DB_PATH)


def init_db() -> None:
    """Create all tables if they do not exist yet."""
    # Import models here to ensure metadata is aware of all tables
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_session():
    """Yield a new database session. Caller is responsible for closing it."""
    return SessionLocal()