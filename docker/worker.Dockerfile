FROM python:3.11-slim-trixie AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.31 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0 UV_NO_DEV=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --extra whisper-worker

ENV PATH="/app/.venv/bin:$PATH"

RUN python -c "import whisper; whisper.load_model('base')"

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --extra whisper-worker


FROM python:3.11-slim-trixie

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /root/.cache/whisper /root/.cache/whisper
COPY --from=builder /app /app

RUN mkdir -p uploads

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

CMD ["celery", "-A", "src.workers.celery_app:celery_app", "worker", \
     "--loglevel=INFO", "--pool=prefork", "--concurrency=1", \
     "--queues=whisper", "--max-tasks-per-child=15"]