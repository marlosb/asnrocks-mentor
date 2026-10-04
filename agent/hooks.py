"""Hooks de segurança da sessão.

Centraliza regras de bloqueio (`on_pre_tool_use`) aplicadas antes de qualquer
chamada de tool. A partir do módulo 6d, a única regra existente é a allowlist
de domínios para a navegação via Playwright MCP (`agent/config.py`): o
Playwright MCP e suas próprias flags `--allowed-origins`/`--blocked-origins`
não são consideradas uma fronteira de segurança pela documentação oficial do
servidor, por isso o bloqueio é feito aqui, do lado do agente.

Novas regras de bloqueio entram neste módulo, com teste em
`tests/test_hooks.py`.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from copilot.session import PreToolUseHookInput, PreToolUseHookOutput

from agent.config import settings

logger = logging.getLogger(__name__)

# Trecho do nome que identifica as tools do Playwright MCP que abrem uma URL
# (navegação ou nova aba). Comparação por substring porque o nome exato da
# tool, visto pelo hook, pode ou não vir prefixado com o nome do servidor MCP
# (ex.: "browser_navigate" ou "playwright-browser_navigate").
_TRECHOS_TOOLS_NAVEGACAO = ("browser_navigate", "browser_tabs")


def _host_permitido(url: str, dominios_permitidos: list[str]) -> bool:
    """Verifica se o host de `url` está na allowlist (ou é subdomínio dela)."""
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    return any(host == dominio or host.endswith(f".{dominio}") for dominio in dominios_permitidos)


async def on_pre_tool_use(
    hook_input: PreToolUseHookInput, _invocation: dict[str, str]
) -> PreToolUseHookOutput | None:
    """Bloqueia a navegação do Playwright MCP para domínios fora da allowlist."""
    nome_tool = hook_input["toolName"]
    if not any(trecho in nome_tool for trecho in _TRECHOS_TOOLS_NAVEGACAO):
        return None

    args = hook_input.get("toolArgs")
    url = args.get("url") if isinstance(args, dict) else None
    if not isinstance(url, str) or not url:
        # Tools sem "url" (ex.: browser_tabs com action="close") não navegam
        # para lugar nenhum; nada a bloquear.
        return None

    dominios_permitidos = settings.lista_dominios_permitidos_navegador()
    if _host_permitido(url, dominios_permitidos):
        return None

    logger.warning("Navegação bloqueada pela allowlist de domínios: %s", url)
    return {
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"Domínio não permitido: '{url}'. Domínios liberados: {', '.join(dominios_permitidos)}."
        ),
    }


__all__ = ["on_pre_tool_use"]
