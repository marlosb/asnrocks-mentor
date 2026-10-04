"""Tool de RAG: `search_docs`, busca no acervo de aulas indexado no Qdrant.

A partir do módulo 6a, o Mentor pode consultar o conteúdo de aulas passadas
(transcrições) via busca semântica. Os chunks são gerados por
`scripts/ingest.py` e vetorizados com o mesmo modelo de embedding usado aqui
na consulta (`FOUNDRY_MODEL_EMBEDDINGS`). O conteúdo retornado é dado não
confiável: nunca é executado como instrução, só consultado como texto.
"""

from __future__ import annotations

import logging

import httpx
from copilot import Tool, define_tool
from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient

from agent.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT_SEGUNDOS = 10.0
_MAX_RESULTADOS = 5
_COLECAO = "aulas"


class BuscarDocumentosParams(BaseModel):
    """Parâmetros da tool `search_docs`."""

    consulta: str = Field(
        description="Pergunta ou termos de busca em linguagem natural, ex.: 'o que é overfitting'"
    )


async def _gerar_embedding_consulta(consulta: str) -> list[float] | None:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SEGUNDOS) as cliente:
            resposta = await cliente.post(
                f"{settings.foundry_base_url}/openai/v1/embeddings",
                headers={"api-key": settings.foundry_api_key},
                json={"model": settings.foundry_model_embeddings, "input": [consulta]},
            )
            resposta.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Falha ao gerar embedding da consulta: %s", exc)
        return None
    return resposta.json()["data"][0]["embedding"]


async def _executar_busca(consulta: str) -> str | dict[str, str]:
    vetor = await _gerar_embedding_consulta(consulta)
    if vetor is None:
        return {
            "erro": "Não foi possível gerar o embedding da consulta no momento.",
            "sugestao": "Tente novamente em instantes.",
        }

    try:
        cliente_qdrant = AsyncQdrantClient(url=settings.qdrant_url)
        if not await cliente_qdrant.collection_exists(_COLECAO):
            return {
                "erro": "O acervo de aulas ainda não foi indexado.",
                "sugestao": "Rode scripts/ingest.ps1 para ingerir as transcrições antes de buscar.",
            }
        resultados = await cliente_qdrant.query_points(
            _COLECAO, query=vetor, limit=_MAX_RESULTADOS, with_payload=True
        )
    except Exception as exc:  # noqa: BLE001 - qualquer falha de conexão/consulta vira erro estruturado
        logger.warning("Falha ao consultar o Qdrant: %s", exc)
        return {
            "erro": "Não foi possível consultar o acervo de aulas no momento.",
            "sugestao": "Verifique se o Qdrant está em execução (docker compose up -d qdrant).",
        }

    pontos = resultados.points
    if not pontos:
        return f"Nenhum trecho encontrado no acervo de aulas para: {consulta}"

    linhas = [f"Trechos do acervo de aulas para '{consulta}':"]
    for ponto in pontos:
        aula = ponto.payload.get("aula", "aula desconhecida") if ponto.payload else "?"
        indice = ponto.payload.get("indice_chunk", "?") if ponto.payload else "?"
        texto = ponto.payload.get("texto", "") if ponto.payload else ""
        linhas.append(
            f"- Fonte: {aula} (trecho #{indice}, relevância {ponto.score:.2f})\n  {texto}"
        )
    return "\n".join(linhas)


@define_tool(
    description=(
        "Busca trechos relevantes no acervo de aulas do curso (transcrições indexadas "
        f"no Qdrant) e retorna até {_MAX_RESULTADOS} trechos, cada um com a aula de "
        "origem e a relevância. Use quando o aluno perguntar sobre algo coberto nas "
        "aulas passadas ou pedir para revisar conteúdo do curso. Não use para "
        "informações atuais da web (use buscar_na_web) nem quando já souber responder "
        "com confiança."
    )
)
async def search_docs(params: BuscarDocumentosParams) -> str | dict[str, str]:
    """Busca semântica no acervo de aulas indexado e retorna os trechos mais relevantes."""
    consulta = params.consulta.strip()
    if not consulta:
        return {
            "erro": "Consulta vazia.",
            "sugestao": "Informe uma pergunta ou termos de busca.",
        }
    return await _executar_busca(consulta)


def criar_tools() -> list[Tool]:
    """Retorna as tools de RAG prontas para registro em `create_session`."""
    return [search_docs]


__all__ = ["BuscarDocumentosParams", "criar_tools"]
