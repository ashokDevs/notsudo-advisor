# NotSudo Advisor — production image (scan + UI + OAuth + PRs)
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NOTSUDO_HASH_EMBEDDINGS=1 \
    PORT=8080

# git is required for "scan any GitHub URL" (shallow clone)
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY api ./api
COPY cli ./cli
COPY core ./core
COPY mcp_server ./mcp_server
COPY frontend ./frontend
COPY demo_app ./demo_app
COPY eval ./eval

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -e .

EXPOSE 8080

# Cloud hosts inject PORT; bind all interfaces for public traffic
CMD ["sh", "-c", "uvicorn api.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
