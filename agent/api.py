"""API FastAPI que encapsula a sessão do agente Mentor.

Expõe `POST /chat` para enviar mensagens e `GET /events` como Server-Sent Events,
transmitindo em tempo real as respostas do agente (e, nos módulos seguintes, os
eventos de uso de tools) para o painel do frontend.

A partir do módulo 2, a sessão carrega a persona do Mentor a partir de
`agent/prompts/mentor.system.md`.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path

from copilot import CopilotClient
from copilot.session import CopilotSession, PermissionHandler
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent.config import settings

logger = logging.getLogger(__name__)

PROMPT_SISTEMA_PATH = Path(__file__).parent / "prompts" / "mentor.system.md"
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


class EstadoAgente:
    """Guarda o cliente/sessão ativos e os assinantes conectados via SSE."""

    def __init__(self) -> None:
        self.client: CopilotClient | None = None
        self.session: CopilotSession | None = None
        self.assinantes: set[asyncio.Queue[dict]] = set()
        self.encerrando: asyncio.Event = asyncio.Event()


estado = EstadoAgente()


def _carregar_prompt_sistema() -> str:
    """Lê o prompt do Mentor, descartando o frontmatter YAML inicial."""
    texto = PROMPT_SISTEMA_PATH.read_text(encoding="utf-8")
    partes = texto.split("---", 2)
    return partes[2].strip() if len(partes) == 3 else texto.strip()


def _serializar_evento(event: object) -> dict:
    """Converte um evento da sessão em um dicionário pronto para JSON.

    Os dados do evento são instâncias de dataclasses geradas pelo SDK (com um
    método `to_dict()`), não modelos Pydantic — por isso a prioridade abaixo.
    """
    tipo = getattr(event, "type", "desconhecido")
    tipo_serializado = tipo.value if isinstance(tipo, Enum) else str(tipo)

    dados = getattr(event, "data", None)
    if dados is not None and hasattr(dados, "to_dict"):
        dados_serializados = dados.to_dict()
    elif dados is not None and hasattr(dados, "model_dump"):
        dados_serializados = dados.model_dump(mode="json")
    else:
        dados_serializados = str(dados)
    return {"tipo": tipo_serializado, "dados": dados_serializados}


def _transmitir_para_assinantes(event: object) -> None:
    """Encaminha um evento da sessão para todos os clientes SSE conectados."""
    payload = _serializar_evento(event)
    if payload["tipo"] == "session.error":
        logger.error("Erro na sessão do agente: %s", payload["dados"])
    for fila in list(estado.assinantes):
        fila.put_nowait(payload)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    client = CopilotClient(base_directory=settings.copilot_home)
    await client.start()
    session = await client.create_session(
        on_permission_request=PermissionHandler.approve_all,
        model=settings.foundry_model,
        provider={
            "type": "azure",
            "base_url": settings.foundry_base_url,
            "api_key": settings.foundry_api_key,
            "wire_api": "responses",
        },
        streaming=True,
        system_message={"mode": "append", "content": _carregar_prompt_sistema()},
    )
    session.on(_transmitir_para_assinantes)

    estado.client = client
    estado.session = session
    try:
        yield
    finally:
        # Sinaliza às conexões SSE abertas para encerrarem imediatamente, em vez de
        # deixar o uvicorn esperar indefinidamente por elas no shutdown gracioso.
        estado.encerrando.set()
        await session.disconnect()
        await client.stop()


app = FastAPI(title="Mentor", lifespan=lifespan)


class MensagemChat(BaseModel):
    mensagem: str


@app.post("/chat")
async def chat(corpo: MensagemChat) -> dict:
    """Envia a mensagem do aluno para a sessão. A resposta chega via /events."""
    if estado.session is None:
        return {"erro": "sessão ainda não iniciada", "sugestao": "tente novamente em instantes"}
    await estado.session.send(corpo.mensagem)
    return {"status": "enviado"}


@app.get("/events")
async def events(request: Request) -> StreamingResponse:
    """Stream SSE com os eventos da sessão (deltas, mensagens finais, fim de turno)."""
    fila: asyncio.Queue[dict] = asyncio.Queue()
    estado.assinantes.add(fila)

    async def transmissor() -> AsyncIterator[str]:
        try:
            while not estado.encerrando.is_set():
                if await request.is_disconnected():
                    break

                tarefa_fila = asyncio.ensure_future(fila.get())
                tarefa_encerrar = asyncio.ensure_future(estado.encerrando.wait())
                concluidas, pendentes = await asyncio.wait(
                    {tarefa_fila, tarefa_encerrar},
                    timeout=15,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for tarefa in pendentes:
                    tarefa.cancel()

                if tarefa_encerrar in concluidas:
                    break
                if tarefa_fila in concluidas:
                    yield f"data: {json.dumps(tarefa_fila.result(), ensure_ascii=False)}\n\n"
                else:
                    yield ": keep-alive\n\n"
        finally:
            estado.assinantes.discard(fila)

    return StreamingResponse(transmissor(), media_type="text/event-stream")


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
