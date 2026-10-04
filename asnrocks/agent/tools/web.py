"""Tools de acesso à web pública: `buscar_na_web` e `ler_pagina_web`.

A partir do módulo 5, o Mentor pode pesquisar e abrir páginas públicas para
responder com informações atuais. O conteúdo retornado por essas tools é dado
não confiável: nunca é executado como instrução, só consultado como texto.
"""

from __future__ import annotations

import logging
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx
from copilot import Tool, define_tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_USER_AGENT = "Mozilla/5.0 (compatible; MentorWorkshopBot/1.0)"
_TIMEOUT_SEGUNDOS = 10.0
_MAX_RESULTADOS_BUSCA = 5
_MAX_CARACTERES_PAGINA = 4000


class BuscarNaWebParams(BaseModel):
    """Parâmetros da tool `buscar_na_web`."""

    consulta: str = Field(description="Termos de busca em linguagem natural, ex.: 'o que é pca'")


class LerPaginaWebParams(BaseModel):
    """Parâmetros da tool `ler_pagina_web`."""

    url: str = Field(description="URL completa (http:// ou https://) da página a ser lida")


class _ExtratorResultadosBusca(HTMLParser):
    """Extrai título, URL e trecho de cada resultado da página de busca do DuckDuckGo."""

    def __init__(self) -> None:
        super().__init__()
        self.resultados: list[dict[str, str]] = []
        self._modo: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        classes = dict(attrs).get("class") or ""
        href = dict(attrs).get("href") or ""
        if "result__a" in classes:
            self._modo = "titulo"
            self.resultados.append({"titulo": "", "url": href, "trecho": ""})
        elif "result__snippet" in classes:
            self._modo = "trecho"

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._modo = None

    def handle_data(self, data: str) -> None:
        if not self.resultados or self._modo is None:
            return
        if self._modo == "titulo":
            self.resultados[-1]["titulo"] += data
        elif self._modo == "trecho":
            self.resultados[-1]["trecho"] += data


class _ExtratorTextoPagina(HTMLParser):
    """Extrai o texto visível de uma página HTML, ignorando script/style/nav/footer."""

    _TAGS_IGNORADAS = {"script", "style", "noscript", "nav", "footer", "header", "svg"}

    def __init__(self) -> None:
        super().__init__()
        self._partes: list[str] = []
        self._profundidade_ignorada = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._TAGS_IGNORADAS:
            self._profundidade_ignorada += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._TAGS_IGNORADAS and self._profundidade_ignorada > 0:
            self._profundidade_ignorada -= 1

    def handle_data(self, data: str) -> None:
        if self._profundidade_ignorada == 0:
            texto = data.strip()
            if texto:
                self._partes.append(texto)

    def texto(self) -> str:
        return "\n".join(self._partes)


async def _executar_busca(consulta: str) -> str | dict[str, str]:
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": _USER_AGENT}, timeout=_TIMEOUT_SEGUNDOS
        ) as cliente:
            resposta = await cliente.post("https://html.duckduckgo.com/html/", data={"q": consulta})
            resposta.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Falha ao buscar na web: %s", exc)
        return {
            "erro": "Não foi possível buscar na web no momento.",
            "sugestao": "Tente novamente em instantes ou reformule a consulta.",
        }

    extrator = _ExtratorResultadosBusca()
    extrator.feed(resposta.text)
    resultados = extrator.resultados[:_MAX_RESULTADOS_BUSCA]

    if not resultados:
        return f"Nenhum resultado encontrado para: {consulta}"

    linhas = [f"Resultados da busca por '{consulta}':"]
    for item in resultados:
        titulo = item["titulo"].strip() or "(sem título)"
        trecho = item["trecho"].strip()
        linhas.append(f"- {titulo}\n  URL: {item['url']}\n  {trecho}")
    return "\n".join(linhas)


@define_tool(
    description=(
        "Busca páginas públicas na web (via DuckDuckGo) e retorna até "
        f"{_MAX_RESULTADOS_BUSCA} resultados, cada um com título, URL e um trecho. "
        "Use quando precisar de informações atuais ou de fontes que não fazem parte "
        "do seu conhecimento. Não use para conteúdo do acervo do curso (aulas e "
        "transcrições) nem quando já souber responder com confiança."
    )
)
async def buscar_na_web(params: BuscarNaWebParams) -> str | dict[str, str]:
    """Busca na web pública e retorna título, URL e trecho de cada resultado."""
    consulta = params.consulta.strip()
    if not consulta:
        return {
            "erro": "Consulta vazia.",
            "sugestao": "Informe os termos de busca.",
        }
    return await _executar_busca(consulta)


async def _executar_leitura(url: str) -> str | dict[str, str]:
    partes = urlparse(url)
    if partes.scheme not in ("http", "https") or not partes.netloc:
        return {
            "erro": f"URL inválida: '{url}'.",
            "sugestao": "Informe uma URL completa, começando com http:// ou https://.",
        }

    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": _USER_AGENT},
            timeout=_TIMEOUT_SEGUNDOS,
            follow_redirects=True,
        ) as cliente:
            resposta = await cliente.get(url)
            resposta.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Falha ao ler página '%s': %s", url, exc)
        return {
            "erro": f"Não foi possível abrir a página: {url}",
            "sugestao": "Verifique se a URL está correta e acessível publicamente.",
        }

    extrator = _ExtratorTextoPagina()
    extrator.feed(resposta.text)
    texto = extrator.texto()

    truncado = len(texto) > _MAX_CARACTERES_PAGINA
    if truncado:
        texto = texto[:_MAX_CARACTERES_PAGINA]

    linhas = [f"Fonte: {url}", "", texto]
    if truncado:
        linhas.append(f"\n[conteúdo truncado em {_MAX_CARACTERES_PAGINA} caracteres]")
    return "\n".join(linhas)


@define_tool(
    description=(
        "Busca o conteúdo textual de uma página pública a partir de uma URL completa "
        "e retorna o texto principal, truncado quando muito longo. Use depois de "
        "identificar uma URL relevante (por exemplo, com buscar_na_web) para ler o "
        "conteúdo completo. Não use para arquivos binários (PDF, imagens) nem para "
        "endereços locais/privados."
    )
)
async def ler_pagina_web(params: LerPaginaWebParams) -> str | dict[str, str]:
    """Lê o texto principal de uma página pública a partir da URL informada."""
    return await _executar_leitura(params.url.strip())


def criar_tools() -> list[Tool]:
    """Retorna as tools de web prontas para registro em `create_session`."""
    return [buscar_na_web, ler_pagina_web]


__all__ = ["BuscarNaWebParams", "LerPaginaWebParams", "criar_tools"]
