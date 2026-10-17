"""Engine, ``SessionLocal`` and the per-request ``get_db`` dependency (T-004; 07 §4).

One session per request, never shared between requests, always closed
(CLAUDE.md § SQLAlchemy / Alembic gotchas).
"""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_config


def build_engine(url: str) -> Engine:
    # Creating an engine does not connect; the URL comes only from ConfigService.
    return create_engine(url, pool_pre_ping=True)


engine: Engine = build_engine(get_config().database_url.get_secret_value())

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session]:
    """FastAPI dependency: ``db: Session = Depends(get_db)``. Commit is the caller's job."""
    with SessionLocal() as db:
        yield db
