"""Tools de memória de longo prazo: `salvar_memoria` e `lembrar`.

A partir do módulo 7, o Mentor grava fatos sobre o aluno (nível, objetivos,
progresso, preferências) numa coleção própria do Qdrant (`memorias`), separada
do acervo de aulas (`aulas`, módulo 6a). Como o agente atende sempre o mesmo
aluno, a coleção inteira já é a memória dele — não há campo "aluno" nem
filtro por estudante.

`buscar_memorias_relevantes` é compartilhada entre a tool `lembrar` (busca
explícita, a pedido do modelo) e o hook `on_user_prompt_submitted`
(`agent/hooks.py`), que injeta automaticamente as memórias relevantes para
cada mensagem do aluno como contexto adicional.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

import httpx
from copilot import Tool, define_tool
from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from agent.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT_SEGUNDOS = 10.0
_MAX_RESULTADOS = 5
_COLECAO = "memorias"
_DIMENSAO_EMBEDDING = 3072  # text-embedding-3-large, mesmo modelo do RAG (scripts/ingest.py)


class SalvarMemoriaParams(BaseModel):
    """Parâmetros da tool `salvar_memoria`."""

    fato: str = Field(
        description="Fato sobre o aluno a lembrar depois, ex.: 'está estudando overfitting, "
        "nível intermediário' ou 'prefere exemplos com dados financeiros'"
    )
    tipo: str = Field(
        description="Categoria do fato, ex.: 'progresso', 'objetivo', 'preferencia', 'nivel'"
    )


class LembrarParams(BaseModel):
    """Parâmetros da tool `lembrar`."""

    consulta: str = Field(
        description="O que buscar na memória do aluno, em linguagem natural, "
        "ex.: 'o que o aluno já estudou sobre redes neurais'"
    )


async def _gerar_embedding(texto: str) -> list[float] | None:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SEGUNDOS) as cliente:
            resposta = await cliente.post(
                f"{settings.foundry_base_url}/openai/v1/embeddings",
                headers={"api-key": settings.foundry_api_key},
                json={"model": settings.foundry_model_embeddings, "input": [texto]},
            )
            resposta.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Falha ao gerar embedding: %s", exc)
        return None
    return resposta.json()["data"][0]["embedding"]


async def _garantir_colecao(cliente_qdrant: AsyncQdrantClient) -> None:
    """Cria a coleção `memorias` no Qdrant se ela ainda não existir."""
    if await cliente_qdrant.collection_exists(_COLECAO):
        return
    await cliente_qdrant.create_collection(
        collection_name=_COLECAO,
        vectors_config=VectorParams(size=_DIMENSAO_EMBEDDING, distance=Distance.COSINE),
    )
    logger.info("Coleção '%s' criada no Qdrant (dimensão=%d).", _COLECAO, _DIMENSAO_EMBEDDING)


async def buscar_memorias_relevantes(consulta: str, limite: int = _MAX_RESULTADOS) -> list[dict]:
    """Busca semântica na memória do aluno. Retorna `[]` em caso de falha ou coleção vazia.

    Usada tanto pela tool `lembrar` quanto pelo hook `on_user_prompt_submitted` — por
    isso falha em silêncio (loga e retorna lista vazia) em vez de levantar exceção: uma
    falha na memória não pode travar o turno de conversa.
    """
    vetor = await _gerar_embedding(consulta)
    if vetor is None:
        return []
    try:
        cliente_qdrant = AsyncQdrantClient(url=settings.qdrant_url)
        if not await cliente_qdrant.collection_exists(_COLECAO):
            return []
        resultados = await cliente_qdrant.query_points(
            _COLECAO, query=vetor, limit=limite, with_payload=True
        )
    except Exception as exc:  # noqa: BLE001 - qualquer falha de conexão/consulta vira lista vazia
        logger.warning("Falha ao consultar a memória no Qdrant: %s", exc)
        return []

    return [
        {
            "fato": ponto.payload.get("fato", "") if ponto.payload else "",
            "tipo": ponto.payload.get("tipo", "?") if ponto.payload else "?",
            "criado_em": ponto.payload.get("criado_em", "?") if ponto.payload else "?",
            "relevancia": ponto.score,
        }
        for ponto in resultados.points
    ]


async def _executar_salvar_memoria(fato: str, tipo: str) -> str | dict[str, str]:
    """Gera o embedding do fato e grava um novo ponto na coleção `memorias`."""
    fato = fato.strip()
    if not fato:
        return {"erro": "Fato vazio.", "sugestao": "Informe o que deve ser lembrado."}

    vetor = await _gerar_embedding(fato)
    if vetor is None:
        return {
            "erro": "Não foi possível gerar o embedding do fato no momento.",
            "sugestao": "Tente novamente em instantes.",
        }

    try:
        cliente_qdrant = AsyncQdrantClient(url=settings.qdrant_url)
        await _garantir_colecao(cliente_qdrant)
        await cliente_qdrant.upsert(
            collection_name=_COLECAO,
            points=[
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vetor,
                    payload={
                        "fato": fato,
                        "tipo": tipo.strip() or "geral",
                        "criado_em": datetime.now(UTC).isoformat(),
                    },
                )
            ],
        )
    except Exception as exc:  # noqa: BLE001 - qualquer falha de conexão/gravação vira erro estruturado
        logger.warning("Falha ao gravar memória no Qdrant: %s", exc)
        return {
            "erro": "Não foi possível gravar a memória no momento.",
            "sugestao": "Verifique se o Qdrant está em execução (docker compose up -d qdrant).",
        }

    return "Memória gravada."


@define_tool(
    description=(
        "Guarda um fato sobre o aluno para lembrar em conversas futuras (nível, objetivos, "
        "progresso, preferências). Use sempre que aprender algo relevante e duradouro sobre "
        "o aluno durante a conversa. Não guarde informações sensíveis nem passageiras "
        "(ex.: o resultado de um exercício pontual)."
    )
)
async def salvar_memoria(params: SalvarMemoriaParams) -> str | dict[str, str]:
    """Wrapper fino da tool: delega a `_executar_salvar_memoria` (testável sem o SDK)."""
    return await _executar_salvar_memoria(params.fato, params.tipo)


async def _executar_lembrar(consulta: str) -> str | dict[str, str]:
    """Busca semântica na memória do aluno e retorna os fatos mais relevantes."""
    consulta = consulta.strip()
    if not consulta:
        return {"erro": "Consulta vazia.", "sugestao": "Informe o que deseja lembrar."}

    memorias = await buscar_memorias_relevantes(consulta)
    if not memorias:
        return f"Nenhuma memória encontrada para: {consulta}"

    linhas = [f"Memórias sobre o aluno relacionadas a '{consulta}':"]
    for memoria in memorias:
        linhas.append(
            f"- [{memoria['tipo']}] {memoria['fato']} (relevância {memoria['relevancia']:.2f}, "
            f"gravado em {memoria['criado_em']})"
        )
    return "\n".join(linhas)


@define_tool(
    description=(
        "Busca na memória de longo prazo o que já se sabe sobre o aluno (nível, objetivos, "
        "progresso, preferências registrados em conversas anteriores). Use quando precisar "
        "relembrar algo específico que não veio automaticamente no contexto da conversa."
    )
)
async def lembrar(params: LembrarParams) -> str | dict[str, str]:
    """Wrapper fino da tool: delega a `_executar_lembrar` (testável sem o SDK)."""
    return await _executar_lembrar(params.consulta)


def criar_tools() -> list[Tool]:
    """Retorna as tools de memória prontas para registro em `create_session`."""
    return [salvar_memoria, lembrar]


__all__ = ["SalvarMemoriaParams", "LembrarParams", "buscar_memorias_relevantes", "criar_tools"]
