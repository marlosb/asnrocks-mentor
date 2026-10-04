"""Testes das tools de memória (módulo 7): `salvar_memoria` e `lembrar`."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from agent.tools.memoria import (
    _executar_lembrar,
    _executar_salvar_memoria,
    buscar_memorias_relevantes,
)


def _ponto(fato: str, tipo: str, score: float) -> AsyncMock:
    ponto = AsyncMock()
    ponto.payload = {"fato": fato, "tipo": tipo, "criado_em": "2026-01-01T00:00:00+00:00"}
    ponto.score = score
    return ponto


@pytest.mark.asyncio
async def test_salvar_memoria_recusa_fato_vazio() -> None:
    resultado = await _executar_salvar_memoria("   ", "progresso")

    assert isinstance(resultado, dict)
    assert "erro" in resultado


@pytest.mark.asyncio
async def test_salvar_memoria_sucesso() -> None:
    cliente_qdrant = AsyncMock()
    cliente_qdrant.collection_exists.return_value = True

    with (
        patch("agent.tools.memoria._gerar_embedding", AsyncMock(return_value=[0.1, 0.2])),
        patch("agent.tools.memoria.AsyncQdrantClient", return_value=cliente_qdrant),
    ):
        resultado = await _executar_salvar_memoria("gosta de exemplos com finanças", "preferencia")

    assert resultado == "Memória gravada."
    cliente_qdrant.upsert.assert_awaited_once()
    pontos = cliente_qdrant.upsert.call_args.kwargs["points"]
    assert pontos[0].payload["fato"] == "gosta de exemplos com finanças"
    assert pontos[0].payload["tipo"] == "preferencia"


@pytest.mark.asyncio
async def test_salvar_memoria_sem_embedding_retorna_erro() -> None:
    with patch("agent.tools.memoria._gerar_embedding", AsyncMock(return_value=None)):
        resultado = await _executar_salvar_memoria("fato qualquer", "geral")

    assert isinstance(resultado, dict)
    assert "erro" in resultado


@pytest.mark.asyncio
async def test_lembrar_recusa_consulta_vazia() -> None:
    resultado = await _executar_lembrar(" ")

    assert isinstance(resultado, dict)
    assert "erro" in resultado


@pytest.mark.asyncio
async def test_lembrar_sem_memorias_encontradas() -> None:
    with patch("agent.tools.memoria.buscar_memorias_relevantes", AsyncMock(return_value=[])):
        resultado = await _executar_lembrar("redes neurais")

    assert resultado == "Nenhuma memória encontrada para: redes neurais"


@pytest.mark.asyncio
async def test_lembrar_formata_memorias_encontradas() -> None:
    memorias = [
        {"fato": "estuda overfitting", "tipo": "progresso", "criado_em": "?", "relevancia": 0.8}
    ]
    with patch("agent.tools.memoria.buscar_memorias_relevantes", AsyncMock(return_value=memorias)):
        resultado = await _executar_lembrar("overfitting")

    assert isinstance(resultado, str)
    assert "estuda overfitting" in resultado
    assert "[progresso]" in resultado


@pytest.mark.asyncio
async def test_buscar_memorias_relevantes_sem_embedding_retorna_lista_vazia() -> None:
    with patch("agent.tools.memoria._gerar_embedding", AsyncMock(return_value=None)):
        resultado = await buscar_memorias_relevantes("qualquer coisa")

    assert resultado == []


@pytest.mark.asyncio
async def test_buscar_memorias_relevantes_sem_colecao_retorna_lista_vazia() -> None:
    cliente_qdrant = AsyncMock()
    cliente_qdrant.collection_exists.return_value = False

    with (
        patch("agent.tools.memoria._gerar_embedding", AsyncMock(return_value=[0.1, 0.2])),
        patch("agent.tools.memoria.AsyncQdrantClient", return_value=cliente_qdrant),
    ):
        resultado = await buscar_memorias_relevantes("qualquer coisa")

    assert resultado == []


@pytest.mark.asyncio
async def test_buscar_memorias_relevantes_sucesso() -> None:
    cliente_qdrant = AsyncMock()
    cliente_qdrant.collection_exists.return_value = True
    resposta_busca = AsyncMock()
    resposta_busca.points = [_ponto("prefere exemplos visuais", "preferencia", 0.91)]
    cliente_qdrant.query_points.return_value = resposta_busca

    with (
        patch("agent.tools.memoria._gerar_embedding", AsyncMock(return_value=[0.1, 0.2])),
        patch("agent.tools.memoria.AsyncQdrantClient", return_value=cliente_qdrant),
    ):
        resultado = await buscar_memorias_relevantes("preferências de ensino")

    assert len(resultado) == 1
    assert resultado[0]["fato"] == "prefere exemplos visuais"
    assert resultado[0]["relevancia"] == 0.91
