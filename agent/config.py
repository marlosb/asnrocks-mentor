"""Configuração central do agente, lida uma única vez a partir de variáveis de ambiente."""

from __future__ import annotations

import logging

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Sufixos de rota que às vezes acabam colados no endpoint por engano: o provider
# "azure" do SDK monta o caminho sozinho e exige apenas o host.
_SUFIXOS_ROTA_INDEVIDOS = ("/openai/v1/responses", "/openai/v1", "/responses")


class Settings(BaseSettings):
    """Configurações do agente Mentor, carregadas de variáveis de ambiente ou `.env`."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Microsoft Foundry (endpoint OpenAI-compatível, BYOK)
    foundry_base_url: str = "https://localhost"
    foundry_api_key: str = ""
    foundry_model: str = "gpt-4o"

    # Segundo modelo opcional, no mesmo endpoint e com a mesma api key — permite
    # comparar respostas de modelos diferentes no dropdown do frontend. Deixe em
    # branco para rodar com um único modelo.
    foundry_model_2: str = ""

    # Modelo de embedding do Foundry (mesmo endpoint/api key dos modelos de chat).
    # Usado pelo script de ingestão (scripts/ingest.py) e pela tool search_docs
    # do RAG — sempre o mesmo modelo para indexar e consultar.
    foundry_model_embeddings: str = ""

    # Banco vetorial (RAG) — Qdrant rodando em container via docker-compose.
    # "http://localhost:6333" funciona com o agente rodando fora do container
    # (scripts/start-agent.ps1); dentro do docker-compose, trocar para
    # "http://qdrant:6333" (nome do serviço vira hostname na rede interna).
    qdrant_url: str = "http://localhost:6333"

    # Sandbox de execução de código Python (módulo 6c). O container roda com
    # network_mode: none (sem rede); a tool run_python invoca código nele via
    # `docker exec <nome>`, por isso o nome precisa ser estável
    # (container_name no docker-compose.yml), não o nome gerado pelo compose.
    sandbox_container_name: str = "mentor-sandbox"
    sandbox_timeout_segundos: int = 20

    # Diretório de dados do runtime do Copilot SDK (sessões, config, etc.).
    # Isolado do perfil pessoal do desenvolvedor (~/.copilot) para que o agente do
    # workshop não herde MCP servers, extensões ou credenciais de outros projetos.
    copilot_home: str = ".copilot-home"

    # API do agente
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    @field_validator("foundry_base_url")
    @classmethod
    def _normalizar_base_url(cls, valor: str) -> str:
        """Remove barra final e sufixos de rota (`/openai/v1`, `/responses`, ...).

        O provider "azure" do SDK espera só o host e monta o caminho sozinho;
        incluir a rota aqui causa erros confusos (ex.: resposta 400 tratando
        "responses" como um ID de resposta).
        """
        normalizado = valor.rstrip("/")
        for sufixo in _SUFIXOS_ROTA_INDEVIDOS:
            if normalizado.endswith(sufixo):
                restante = normalizado[: -len(sufixo)]
                logger.warning(
                    "FOUNDRY_BASE_URL continha o sufixo '%s'; usando apenas o host: %s",
                    sufixo,
                    restante,
                )
                return restante
        return normalizado

    def modelos_disponiveis(self) -> list[str]:
        """Lista dos modelos configurados, compartilhando a mesma api key."""
        modelos = [self.foundry_model]
        if self.foundry_model_2:
            modelos.append(self.foundry_model_2)
        return modelos


settings = Settings()
