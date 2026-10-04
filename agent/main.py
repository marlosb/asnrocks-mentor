"""Demo do módulo 1: o primeiro agente, em poucas linhas.

Cria um cliente, abre uma sessão apontando para o Microsoft Foundry (BYOK) e envia
um único prompt, imprimindo a resposta. Ainda sem prompt de sistema ou persona
(isso chega no módulo 2) — é o agente genérico do harness. Rode com:

    uv run python agent/main.py
"""

from __future__ import annotations

import asyncio

from copilot import CopilotClient
from copilot.session import PermissionHandler

from agent.config import settings


async def main() -> None:
    async with CopilotClient(base_directory=settings.copilot_home) as client:
        async with await client.create_session(
            on_permission_request=PermissionHandler.approve_all,
            model=settings.foundry_model,
            provider={
                "type": "azure",
                "base_url": settings.foundry_base_url,
                "api_key": settings.foundry_api_key,
                "wire_api": "responses",
            },
        ) as session:
            resposta = await session.send_and_wait("Olá! Quem é você?")
            print(resposta)


if __name__ == "__main__":
    asyncio.run(main())
