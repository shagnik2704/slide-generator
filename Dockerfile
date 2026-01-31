FROM python:3.11-slim


RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

ENV PATH="/app/.venv/bin:$PATH"


RUN python -c "import whisper; whisper.load_model('base')"

COPY src/ ./src/

RUN mkdir -p uploads output data static

EXPOSE 8000

CMD ["uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]