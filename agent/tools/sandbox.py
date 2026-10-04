"""Tool de execução de código Python em sandbox isolado (`run_python`).

A partir do módulo 6c, o Mentor pode executar trechos de Python para
demonstrar conceitos com exemplos práticos. O código roda sempre dentro do
container `sandbox/` — sem rede (`network_mode: none`), sistema de arquivos
somente leitura (exceto `/tmp`), sem capabilities extras e com limites de
CPU/memória — nunca no processo do agente nem no host. A tool invoca o
container via `docker exec`, que fala com o daemon do Docker e não depende da
rede do container (por isso funciona apesar do isolamento de rede).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable

from copilot import Tool, ToolBinaryResult, ToolResult, define_tool
from pydantic import BaseModel, Field

from agent.config import settings

logger = logging.getLogger(__name__)

# Tempo extra além do timeout interno do sandbox, para cobrir a sobrecarga do
# próprio `docker exec` (start do processo, I/O de stdin/stdout).
_MARGEM_TIMEOUT_SEGUNDOS = 5


class ExecutarPythonParams(BaseModel):
    """Parâmetros da tool `run_python`."""

    codigo: str = Field(description="Código Python a ser executado no sandbox")


async def _executar_no_sandbox(codigo: str) -> dict:
    """Roda o código no container do sandbox via `docker exec` e devolve o resultado bruto."""
    timeout_total = settings.sandbox_timeout_segundos + _MARGEM_TIMEOUT_SEGUNDOS
    try:
        processo = await asyncio.create_subprocess_exec(
            "docker",
            "exec",
            "-i",
            settings.sandbox_container_name,
            "python",
            "server.py",
            str(settings.sandbox_timeout_segundos),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            processo.communicate(codigo.encode("utf-8")), timeout=timeout_total
        )
    except TimeoutError:
        return {
            "erro": f"Execução excedeu o limite de {timeout_total}s e foi abortada.",
            "sugestao": "Simplifique o código ou reduza o volume de dados processados.",
        }
    except FileNotFoundError:
        logger.error("Comando 'docker' não encontrado no PATH do agente.")
        return {
            "erro": "Sandbox indisponível: Docker não encontrado.",
            "sugestao": "Verifique se o Docker Desktop está em execução.",
        }
    except OSError as exc:
        logger.warning("Falha ao invocar o sandbox: %s", exc)
        return {
            "erro": "Não foi possível executar o código no sandbox no momento.",
            "sugestao": (
                "Verifique se o container do sandbox está em execução "
                "(docker compose up -d sandbox)."
            ),
        }

    if processo.returncode != 0:
        detalhe = stderr_bytes.decode("utf-8", errors="replace").strip()
        logger.warning("docker exec retornou código %s: %s", processo.returncode, detalhe)
        return {
            "erro": "Não foi possível executar o código no sandbox no momento.",
            "sugestao": (
                "Verifique se o container do sandbox está em execução "
                "(docker compose up -d sandbox)."
            ),
        }

    try:
        return json.loads(stdout_bytes.decode("utf-8"))
    except json.JSONDecodeError:
        logger.warning("Saída inesperada do sandbox: %s", stdout_bytes[:500])
        return {
            "erro": "O sandbox retornou uma saída inesperada.",
            "sugestao": "Tente novamente com um código mais simples.",
        }


def _montar_resultado(resultado: dict) -> str | ToolResult:
    """Converte o JSON bruto do sandbox num resultado pronto para o modelo."""
    if set(resultado) == {"erro", "sugestao"}:
        return resultado  # type: ignore[return-value] # erro de infraestrutura, já estruturado

    linhas = []
    if resultado.get("stdout"):
        linhas.append(f"Saída:\n{resultado['stdout']}")
    if resultado.get("erro"):
        linhas.append(f"Erro de execução:\n{resultado['erro']}")
    if resultado.get("stderr"):
        linhas.append(f"stderr:\n{resultado['stderr']}")
    imagens = resultado.get("imagens") or []
    if imagens:
        linhas.append(f"[{len(imagens)} imagem(ns) gerada(s), anexadas ao resultado]")
    if not linhas:
        linhas.append("Execução concluída sem saída.")
    texto = "\n\n".join(linhas)

    if not imagens:
        return texto
    return ToolResult(
        text_result_for_llm=texto,
        binary_results_for_llm=[
            ToolBinaryResult(
                data=imagem,
                mime_type="image/png",
                type="image",
                description=f"Gráfico {i + 1} gerado pelo código executado",
            )
            for i, imagem in enumerate(imagens)
        ],
    )


def criar_tools(publicar_imagens: Callable[[list[str]], None] | None = None) -> list[Tool]:
    """Retorna as tools de sandbox prontas para registro em `create_session`.

    `publicar_imagens`, se informado, é chamado com a lista de imagens (PNG em
    base64) sempre que o código executado gerar gráficos. O SDK não ecoa o
    conteúdo binário dos resultados de tool pelos eventos da sessão (ele vai
    só para o modelo, para a própria resposta) — por isso, sem esse canal
    próprio, o frontend não teria como exibir os gráficos gerados.
    """

    async def run_python(params: ExecutarPythonParams) -> str | dict | ToolResult:
        """Executa código Python no sandbox e retorna o resultado estruturado."""
        codigo = params.codigo.strip()
        if not codigo:
            return {"erro": "Código vazio.", "sugestao": "Informe o código Python a executar."}

        resultado = await _executar_no_sandbox(codigo)
        imagens = resultado.get("imagens") or []
        if imagens and publicar_imagens is not None:
            publicar_imagens(imagens)
        return _montar_resultado(resultado)

    tool = define_tool(
        "run_python",
        description=(
            "Executa um trecho de código Python em um sandbox isolado (sem rede, "
            "sem acesso ao host) e retorna stdout, stderr e eventuais gráficos "
            "matplotlib gerados. Use para demonstrar conceitos com exemplos "
            "executáveis (ex.: mostrar como regressão logística funciona na "
            "prática). Não use para ler/escrever arquivos do projeto nem para "
            "acessar a rede — o sandbox não tem esses acessos."
        ),
        handler=lambda params, _invocation: run_python(params),
        params_type=ExecutarPythonParams,
    )
    return [tool]


__all__ = ["ExecutarPythonParams", "criar_tools"]
