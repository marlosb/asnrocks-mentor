"""Testes do módulo de configuração do agente."""

from __future__ import annotations

from agent.config import Settings


def test_settings_usa_valores_padrao_quando_sem_env() -> None:
    config = Settings(_env_file=None)  # type: ignore[call-arg]

    assert config.foundry_model == "gpt-4o"
    assert config.app_port == 8000


def test_settings_le_variaveis_de_ambiente(monkeypatch) -> None:
    monkeypatch.setenv("FOUNDRY_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("APP_PORT", "9000")

    config = Settings(_env_file=None)  # type: ignore[call-arg]

    assert config.foundry_model == "gpt-4o-mini"
    assert config.app_port == 9000


def test_settings_remove_sufixo_de_rota_do_base_url(monkeypatch) -> None:
    monkeypatch.setenv(
        "FOUNDRY_BASE_URL", "https://meu-recurso.services.ai.azure.com/openai/v1/responses"
    )

    config = Settings(_env_file=None)  # type: ignore[call-arg]

    assert config.foundry_base_url == "https://meu-recurso.services.ai.azure.com"


def test_settings_remove_barra_final_do_base_url(monkeypatch) -> None:
    monkeypatch.setenv("FOUNDRY_BASE_URL", "https://meu-recurso.services.ai.azure.com/")

    config = Settings(_env_file=None)  # type: ignore[call-arg]

    assert config.foundry_base_url == "https://meu-recurso.services.ai.azure.com"
