"""Executa código Python recebido via stdin, com timeout e captura de saída/imagens.

Invocado via `docker exec -i <container> python server.py <timeout>` pela tool
`run_python` (agent/tools/sandbox.py). Roda sempre dentro do container do
sandbox (sem rede, sistema de arquivos somente leitura exceto /tmp) — nunca é
chamado diretamente pelo agente ou no host.
"""

from __future__ import annotations

import base64
import io
import json
import signal
import sys
import traceback
from types import FrameType


class _TimeoutExecucao(Exception):
    """Levantada quando o alarme de timeout dispara durante a execução do código."""


def _handler_timeout(signum: int, frame: FrameType | None) -> None:
    raise _TimeoutExecucao


def main() -> None:
    codigo = sys.stdin.read()
    timeout_segundos = int(sys.argv[1]) if len(sys.argv) > 1 else 20

    captura_stdout = io.StringIO()
    captura_stderr = io.StringIO()
    imagens: list[str] = []
    erro: str | None = None

    stdout_original, stderr_original = sys.stdout, sys.stderr
    signal.signal(signal.SIGALRM, _handler_timeout)
    signal.alarm(timeout_segundos)
    try:
        sys.stdout, sys.stderr = captura_stdout, captura_stderr

        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        exec(codigo, {"__name__": "__main__"})  # noqa: S102 - propósito do sandbox é executar código do aluno

        for numero in plt.get_fignums():
            buffer = io.BytesIO()
            plt.figure(numero).savefig(buffer, format="png", bbox_inches="tight")
            imagens.append(base64.b64encode(buffer.getvalue()).decode("ascii"))
        plt.close("all")
    except _TimeoutExecucao:
        erro = f"Execução excedeu o limite de {timeout_segundos}s e foi interrompida."
    except Exception:
        erro = traceback.format_exc()
    finally:
        signal.alarm(0)
        sys.stdout, sys.stderr = stdout_original, stderr_original

    resultado = {
        "stdout": captura_stdout.getvalue(),
        "stderr": captura_stderr.getvalue(),
        "erro": erro,
        "imagens": imagens,
    }
    print(json.dumps(resultado))


if __name__ == "__main__":
    main()
