"""Testes dos hooks da sessão: bloqueio de tools (módulo 6d) e memória (módulo 7)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from copilot.session import PreToolUseHookInput, UserPromptSubmittedHookInput

from agent.hooks import on_pre_tool_use, on_user_prompt_submitted


def _hook_input(nome_tool: str, tool_args: object) -> PreToolUseHookInput:
    return {
        "sessionId": "teste",
        "timestamp": datetime.now(UTC),
        "workingDirectory": ".",
        "toolName": nome_tool,
        "toolArgs": tool_args,
    }


@pytest.mark.asyncio
async def test_permite_navegacao_para_dominio_na_allowlist() -> None:
    entrada = _hook_input("browser_navigate", {"url": "https://docs.python.org/3/"})

    resultado = await on_pre_tool_use(entrada, {})

    assert resultado is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "https://bcb.gov.br/",
        "https://www.bcb.gov.br/",
        "https://api.bcb.gov.br/",
    ],
)
async def test_permite_navegacao_para_banco_central(url: str) -> None:
    entrada = _hook_input("playwright-browser_navigate", {"url": url})

    resultado = await on_pre_tool_use(entrada, {})

    assert resultado is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "https://bcb.gov.br.exemplo.com/",
        "https://falsobcb.gov.br/",
        "https://www.outro.gov.br/",
    ],
)
async def test_bloqueia_dominios_fora_do_banco_central(url: str) -> None:
    entrada = _hook_input("playwright-browser_navigate", {"url": url})

    resultado = await on_pre_tool_use(entrada, {})

    assert resultado is not None
    assert resultado["permissionDecision"] == "deny"


@pytest.mark.asyncio
async def test_bloqueia_navegacao_para_dominio_fora_da_allowlist() -> None:
    entrada = _hook_input("browser_navigate", {"url": "https://exemplo-malicioso.com/"})

    resultado = await on_pre_tool_use(entrada, {})

    assert resultado is not None
    assert resultado["permissionDecision"] == "deny"
    assert "exemplo-malicioso.com" in resultado["permissionDecisionReason"]


@pytest.mark.asyncio
async def test_permite_subdominio_de_dominio_na_allowlist() -> None:
    entrada = _hook_input("browser_navigate", {"url": "https://pt.wikipedia.org/wiki/Python"})

    resultado = await on_pre_tool_use(entrada, {})

    assert resultado is None


@pytest.mark.asyncio
async def test_ignora_tools_que_nao_navegam() -> None:
    entrada = _hook_input("browser_click", {"target": "ref=1"})

    resultado = await on_pre_tool_use(entrada, {})

    assert resultado is None


@pytest.mark.asyncio
async def test_ignora_tool_de_navegacao_sem_url() -> None:
    entrada = _hook_input("browser_tabs", {"action": "close", "index": 1})

    resultado = await on_pre_tool_use(entrada, {})

    assert resultado is None


@pytest.mark.asyncio
async def test_funciona_com_prefixo_do_servidor_mcp() -> None:
    """O nome visto pelo hook pode vir prefixado com o nome do servidor MCP."""
    entrada = _hook_input("playwright-browser_navigate", {"url": "https://exemplo.com/"})

    resultado = await on_pre_tool_use(entrada, {})

    assert resultado is not None
    assert resultado["permissionDecision"] == "deny"


def _prompt_input(prompt: str) -> UserPromptSubmittedHookInput:
    return {
        "sessionId": "teste",
        "timestamp": datetime.now(UTC),
        "workingDirectory": ".",
        "prompt": prompt,
    }


@pytest.mark.asyncio
async def test_ignora_prompt_vazio() -> None:
    resultado = await on_user_prompt_submitted(_prompt_input("   "), {})

    assert resultado is None


@pytest.mark.asyncio
async def test_nao_injeta_contexto_sem_memorias_relevantes() -> None:
    with patch("agent.hooks.buscar_memorias_relevantes", AsyncMock(return_value=[])):
        resultado = await on_user_prompt_submitted(_prompt_input("oi, tudo bem?"), {})

    assert resultado is None


@pytest.mark.asyncio
async def test_injeta_memorias_relevantes_como_contexto() -> None:
    memorias = [{"fato": "está estudando overfitting", "tipo": "progresso"}]
    with patch("agent.hooks.buscar_memorias_relevantes", AsyncMock(return_value=memorias)):
        resultado = await on_user_prompt_submitted(_prompt_input("o que eu estava vendo?"), {})

    assert resultado is not None
    assert "está estudando overfitting" in resultado["additionalContext"]
    assert "[progresso]" in resultado["additionalContext"]
