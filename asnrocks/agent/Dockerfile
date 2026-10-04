FROM python:3.12-slim

WORKDIR /app

RUN useradd --create-home --shell /bin/bash mentor
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project

COPY agent/ ./agent/
COPY frontend/ ./frontend/
RUN uv sync --no-dev

USER mentor
EXPOSE 8000

CMD ["uv", "run", "uvicorn", "agent.api:app", "--host", "0.0.0.0", "--port", "8000"]
