"""Testes dos hooks de segurança da sessão (módulo 6d)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from copilot.session import PreToolUseHookInput

from agent.hooks import on_pre_tool_use


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
