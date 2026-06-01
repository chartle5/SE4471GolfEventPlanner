# Golf Planner — FastAPI backend
# Base image per spec.
FROM python:3.11-slim

# Faster, cleaner Python in containers.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build deps for packages that may need compilation (bcrypt, etc.).
# Removed in the same layer to keep the image small.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first so this layer is cached across code changes.
# NOTE: requirements.txt is intentionally left unchanged. langchain /
# langchain-anthropic / sentence-transformers are load-bearing (imported at
# startup by app.main -> app.services.rag and the chat agent), so they stay.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# App code.
COPY app ./app

# uvicorn binds to $PORT (defaults to 8000 if unset). The container listens on
# 8000 internally; docker-compose maps it to the host.
ENV PORT=8000
EXPOSE 8000

# Shell form so $PORT is expanded at runtime.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
