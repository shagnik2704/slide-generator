FROM python:3.11-slim


RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache && rm -rf ~/.cache/uv ~/.cache/pip 

ENV PATH="/app/.venv/bin:$PATH"


COPY version-change-automation-abc4823f94ae.json /app/credentials.json


ENV GOOGLE_APPLICATION_CREDENTIALS="/app/credentials.json"

COPY src/ ./src/
COPY migrations/ ./migrations/
COPY alembic.ini ./alembic.ini

RUN mkdir -p uploads output data static

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
