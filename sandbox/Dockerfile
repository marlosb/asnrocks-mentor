# Container de execução de código isolado (módulo 6c). Roda com network_mode:
# none, read_only root filesystem (exceto /tmp) e cap_drop: ALL — ver
# docker-compose.yml. O processo principal fica ocioso (tail -f /dev/null); a
# execução de código acontece via `docker exec` (agent/tools/sandbox.py),
# nunca por rede.
FROM python:3.12-slim

# Em redes corporativas que bloqueiam o PyPI público, sobrescreva com
# `docker compose build --build-arg PIP_INDEX_URL=<espelho interno>`.
ARG PIP_INDEX_URL=https://pypi.org/simple

RUN pip install --no-cache-dir --index-url "$PIP_INDEX_URL" \
        numpy pandas matplotlib scikit-learn \
    && useradd --create-home --uid 1000 sandbox

# Cache de fontes do matplotlib precisa de um diretório gravável; /tmp é o
# único ponto de montagem com escrita permitida (tmpfs, ver docker-compose).
ENV MPLCONFIGDIR=/tmp/mplconfig

USER sandbox
WORKDIR /home/sandbox
COPY --chown=sandbox:sandbox server.py server.py

CMD ["tail", "-f", "/dev/null"]
