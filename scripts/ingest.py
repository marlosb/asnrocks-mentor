"""Script auxiliar de ingestão do acervo de aulas no Qdrant (RAG do módulo 6a).

Lê os arquivos `.txt` de um diretório (transcrições de aula), divide cada um em
chunks de tamanho fixo (em palavras, com sobreposição), gera embeddings via
Microsoft Foundry e grava os pontos na coleção do Qdrant.

Rodar só uma vez por aula nova (ou sempre que o acervo mudar); não faz parte do
runtime do agente.

Exemplo:
    uv run python scripts/ingest.py --origem transcrições
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from agent.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DIMENSAO_EMBEDDING = 3072  # text-embedding-3-large
TAMANHO_LOTE_EMBEDDING = 16  # chunks por chamada ao endpoint de embeddings


@dataclass
class Chunk:
    """Um pedaço de uma aula, pronto para virar um ponto no Qdrant."""

    aula: str
    indice_chunk: int
    texto: str


def _dividir_em_chunks(texto: str, aula: str, tamanho_chunk: int, overlap: int) -> list[Chunk]:
    """Divide o texto em chunks de `tamanho_chunk` palavras, com `overlap` de sobreposição."""
    palavras = texto.split()
    passo = tamanho_chunk - overlap
    chunks = []
    indice = 0
    inicio = 0
    while inicio < len(palavras):
        fim = inicio + tamanho_chunk
        trecho = " ".join(palavras[inicio:fim])
        chunks.append(Chunk(aula=aula, indice_chunk=indice, texto=trecho))
        indice += 1
        if fim >= len(palavras):
            break
        inicio += passo
    return chunks


def _gerar_embeddings(cliente_http: httpx.Client, textos: list[str]) -> list[list[float]]:
    """Chama o endpoint de embeddings do Foundry (OpenAI-compatível) para um lote de textos."""
    resposta = cliente_http.post(
        f"{settings.foundry_base_url}/openai/v1/embeddings",
        headers={"api-key": settings.foundry_api_key},
        json={"model": settings.foundry_model_embeddings, "input": textos},
    )
    resposta.raise_for_status()
    dados = resposta.json()["data"]
    return [item["embedding"] for item in dados]


def _garantir_colecao(cliente_qdrant: QdrantClient, colecao: str) -> None:
    """Cria a coleção no Qdrant se ela ainda não existir."""
    if cliente_qdrant.collection_exists(colecao):
        logger.info("Coleção '%s' já existe; os chunks serão adicionados a ela.", colecao)
        return
    cliente_qdrant.create_collection(
        collection_name=colecao,
        vectors_config=VectorParams(size=DIMENSAO_EMBEDDING, distance=Distance.COSINE),
    )
    logger.info("Coleção '%s' criada (dimensão=%d, distância=cosine).", colecao, DIMENSAO_EMBEDDING)


def ingerir(origem: Path, colecao: str, tamanho_chunk: int, overlap: int) -> None:
    arquivos = sorted(origem.glob("*.txt"))
    if not arquivos:
        logger.warning("Nenhum arquivo .txt encontrado em %s", origem)
        return

    cliente_qdrant = QdrantClient(url=settings.qdrant_url)
    _garantir_colecao(cliente_qdrant, colecao)

    with httpx.Client(timeout=60.0) as cliente_http:
        proximo_id = cliente_qdrant.count(colecao).count
        for arquivo in arquivos:
            aula = arquivo.stem
            texto = arquivo.read_text(encoding="utf-8")
            chunks = _dividir_em_chunks(texto, aula, tamanho_chunk, overlap)
            logger.info("%s: %d chunks (%d palavras)", aula, len(chunks), len(texto.split()))

            for inicio_lote in range(0, len(chunks), TAMANHO_LOTE_EMBEDDING):
                lote = chunks[inicio_lote : inicio_lote + TAMANHO_LOTE_EMBEDDING]
                embeddings = _gerar_embeddings(cliente_http, [c.texto for c in lote])
                pontos = [
                    PointStruct(
                        id=proximo_id + i,
                        vector=embedding,
                        payload={
                            "aula": chunk.aula,
                            "indice_chunk": chunk.indice_chunk,
                            "texto": chunk.texto,
                        },
                    )
                    for i, (chunk, embedding) in enumerate(zip(lote, embeddings, strict=True))
                ]
                cliente_qdrant.upsert(collection_name=colecao, points=pontos)
                proximo_id += len(pontos)
                logger.info("  lote %d-%d gravado", inicio_lote, inicio_lote + len(lote) - 1)

    logger.info(
        "Ingestão concluída. Total de pontos na coleção: %d", cliente_qdrant.count(colecao).count
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--origem", type=Path, default=Path("transcrições"), help="Diretório com os .txt das aulas"
    )
    parser.add_argument("--colecao", default="aulas", help="Nome da coleção no Qdrant")
    parser.add_argument(
        "--tamanho-chunk", type=int, default=500, help="Tamanho do chunk em palavras"
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=50,
        help="Sobreposição entre chunks, em palavras (10%% do padrão)",
    )
    args = parser.parse_args()

    if not settings.foundry_model_embeddings:
        parser.error("FOUNDRY_MODEL_EMBEDDINGS não configurado (veja secrets.txt / .env)")

    ingerir(args.origem, args.colecao, args.tamanho_chunk, args.overlap)


if __name__ == "__main__":
    main()
