# ActaFlow - Motor de IA (voz a texto + extraccion de entidades)
# Imagen pensada para Render Free: CPU sin GPU, 512 MB de RAM y disco efimero.
# Por eso los modelos se descargan AQUI, durante la construccion, y no al arrancar.

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# espeak-ng solo se usa para generar el audio sintetico del benchmark.
RUN apt-get update \
    && apt-get install -y --no-install-recommends espeak-ng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install . \
    && rm -rf /root/.cache

# Modelo de spaCy en espanol (se publica en GitHub, no en PyPI).
ARG SPACY_MODELO_URL=https://github.com/explosion/spacy-models/releases/download/es_core_news_sm-3.8.0/es_core_news_sm-3.8.0-py3-none-any.whl
RUN pip install "${SPACY_MODELO_URL}"

# Modelos de faster-whisper dentro de la imagen. En CI se construye solo con "tiny".
ARG ASR_MODELOS="tiny base small"
RUN HF_HOME=/tmp/hf python -m actaflow_engine.herramientas.descargar_modelos \
        --destino /models ${ASR_MODELOS} \
    && rm -rf /tmp/hf

# Audio sintetico en espanol para el benchmark (lee el mismo guion que usamos como referencia).
RUN mkdir -p /app/muestras \
    && espeak-ng -v es -s 145 \
        -f src/actaflow_engine/diagnostico/muestras/guion_es.txt \
        -w /app/muestras/muestra_es.wav

RUN useradd --system --uid 10001 --no-create-home motor \
    && chown -R motor /app/muestras
USER motor

ENV ACTAFLOW_ENGINE_MODELS_DIR=/models \
    ACTAFLOW_ENGINE_BENCHMARK_AUDIO=/app/muestras/muestra_es.wav \
    ACTAFLOW_ENGINE_ENVIRONMENT=produccion \
    HF_HUB_OFFLINE=1

EXPOSE 8002

# Render inyecta PORT; en local se usa 8002. Un solo proceso: la CPU gratuita no da para mas.
CMD ["sh", "-c", "exec uvicorn --factory actaflow_engine.main:create_app --host 0.0.0.0 --port ${PORT:-8002} --workers 1 --no-server-header --no-access-log"]
