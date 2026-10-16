# Mentor — workshop "Construindo um agente de IA na prática"

Este repositório é o material de acompanhamento do curso/workshop de 4 horas
**"Construindo um agente de IA na prática"**. Ao longo das aulas, construímos o
**Mentor**, um tutor para pessoas que estão aprendendo ciência de dados e IA.

O código evolui junto com o curso: os commits seguem a sequência dos módulos e
registram a inclusão de cada capacidade do agente. Use o histórico para acompanhar
as explicações, comparar as etapas e consultar o código no ponto correspondente à aula.

## Módulos e commits

A tabela apresenta a evolução já implementada, na ordem de construção do Mentor.
Commits de ajustes podem aparecer entre as etapas.

| Etapa do curso | Commit | O que foi adicionado |
|---|---|---|
| Módulo 1 — harness | `7f5261f` | Harness do Mentor, API FastAPI e frontend de chat com streaming via SSE. |
| Módulo 2 — system prompt | `2b445e4` | Persona e orientações do Mentor via system prompt. |
| Módulo 3 — Microsoft Foundry | `2a65424` | Suporte a múltiplos modelos no Microsoft Foundry. |
| Módulo 4 — skills | `6302246` | Skill `explicar-conceito` e resumo de uso no frontend. |
| Módulo 5 — tools | `2e23d7b` | Tools `buscar_na_web` e `ler_pagina_web`. |
| Módulo 6a — RAG | `8b4f52f` | Qdrant, ingestão de aulas e tool `search_docs`. |
| Módulo 6c — sandbox | `ec50a38` | Execução de Python em sandbox isolado via Docker. |
| Módulos 6b/6d — MCP e navegador | `c4e6899` | Automação de navegador via Playwright MCP. |
| Módulo 7 — memória | `2a5b81a` | Memória de longo prazo sobre o aluno. |

Para acompanhar as mudanças de uma etapa, consulte seu commit:

```bash
git show 7f5261f
```

Para listar o histórico na ordem das aulas:

```bash
git log --reverse --oneline
```

## Estrutura do projeto

- `agent/main.py`: montagem e execução da sessão do agente com o GitHub Copilot SDK.
- `agent/api.py`: API FastAPI (`POST /chat`, `GET /events` via SSE) que serve também o frontend.
- `agent/tools/`: tools de pesquisa, consulta ao acervo, execução de Python e memória.
- `frontend/`: chat em HTML/CSS/JavaScript puro, com streaming via SSE.
- `sandbox/`: ambiente isolado para execução de código Python.
- `docker-compose.yml`: serviços do agente, Qdrant, sandbox e Playwright MCP.
- `tests/`: testes automatizados.

As regras e convenções do projeto estão em `.github/copilot-instructions.md`.

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
