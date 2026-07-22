# ---- Stage 1: build dependencies into a virtualenv using uv ----
FROM python:3.12-slim AS builder

# uv is a fast, drop-in Python package manager (https://github.com/astral-sh/uv).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_LINK_MODE=copy

# Copy only dependency metadata first for better layer caching.
COPY pyproject.toml ./
COPY app ./app
RUN uv venv /opt/venv && VIRTUAL_ENV=/opt/venv uv pip install .

# ---- Stage 2: slim runtime image ----
FROM python:3.12-slim AS runtime

RUN groupadd -r app && useradd -r -g app app
WORKDIR /app

# Bring in the prebuilt virtualenv.
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY pyproject.toml ./

USER app
EXPOSE 8000

# The app runs migrations + seed on startup via the FastAPI lifespan, so we just
# launch uvicorn. (For prod, gunicorn+uvicorn workers — see DEPLOY.md.)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
