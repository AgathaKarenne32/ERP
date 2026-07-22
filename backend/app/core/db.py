from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

# SQLite (used in tests) needs check_same_thread disabled; Postgres ignores it.
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args=_connect_args,
    pool_pre_ping=True,
)


def create_db_and_tables() -> None:
    """Create tables from SQLModel metadata.

    For the MVP we bootstrap the schema with create_all on startup (idempotent),
    which keeps local dev to a single `docker compose up`. Alembic migrations are
    included for production/versioned schema changes (see alembic/).
    """
    # Import models so their tables are registered on SQLModel.metadata.
    import app.models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
