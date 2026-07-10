FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ ./src/
COPY queries/ ./queries/
COPY prompts/ ./prompts/
COPY docs/ ./docs/

CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "3600", "--workers", "1", "src.main:app"]
