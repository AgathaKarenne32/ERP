import os

# Configure a throwaway SQLite DB and disable auto-seed BEFORE importing the app,
# so tests run hermetically without Postgres or demo data.
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["RUN_SEED"] = "false"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["ANTHROPIC_API_KEY"] = ""  # forces the AI service into offline demo mode

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from app.core.db import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
