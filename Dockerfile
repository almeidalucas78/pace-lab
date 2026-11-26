# syntax=docker/dockerfile:1
# Imagem do Pace Lab para o servidor (fase 9, etapa 10): API (FastAPI) e o painel compilado na mesma porta.
# Montada no GitHub Actions para amd64 (Oracle E2.1.Micro) e arm64 (Oracle A1); roda com infra/servidor/compose.yaml.

# 1) Painel: o resultado (HTML, JS, CSS) não depende da arquitetura, então compila uma vez, na máquina do build.
FROM --platform=$BUILDPLATFORM node:24-alpine AS painel
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# 2) Servidor Python.
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PACELAB_RAIZ=/app
WORKDIR /app
COPY server/ /tmp/server/
RUN pip install /tmp/server && rm -rf /tmp/server
COPY --from=painel /web/dist /app/web/dist
# Sem root: o processo só escreve em /app/data (volume com APK publicado e arquivos do chat).
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin pacelab \
    && mkdir -p /app/data && chown pacelab:pacelab /app/data
USER pacelab
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"]
# `treino servico` aplica as migrações do banco antes de abrir a porta.
CMD ["treino", "servico", "--host", "0.0.0.0", "--porta", "8000"]
