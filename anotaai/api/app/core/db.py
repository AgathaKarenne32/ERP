from sqlmodel import Session, SQLModel, create_engine

from .config import settings

engine = create_engine(settings.database_url, echo=False)


def init_db() -> None:
    """Bootstrap do schema via create_all (fase 0/MVP). Migrações versionadas
    ficam em alembic/ para as mudanças subsequentes em produção."""
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
