# Mentor — workshop "Construindo um agente de IA na prática"

Agente de IA **Mentor**, construído módulo a módulo durante um workshop de 4 horas.
Veja as regras completas do projeto em `.github/copilot-instructions.md`.

## Módulo 1 — fundação do projeto

- `agent/main.py`: demo mínima do agente (cliente, sessão, prompt, resposta).
- `agent/api.py`: API FastAPI (`POST /chat`, `GET /events` via SSE) que serve também o frontend.
- `frontend/`: chat simples em HTML/CSS/JavaScript puro, com streaming via SSE.

## Como rodar

```bash
# Instalar dependências
uv sync

# Configurar o acesso ao Microsoft Foundry
cp .env.example .env   # edite com seu endpoint e chave

# Demo de linha de comando
uv run python agent/main.py

# API + frontend
uv run uvicorn agent.api:app --reload --port 8000
# abra http://localhost:8000

# Ou via Docker Compose
docker compose up -d agent
```

## Qualidade

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy agent
uv run pytest
```
