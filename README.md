# ActaFlow · Motor de IA

Motor de **voz a texto** y **extracción de entidades jurídicas** de ActaFlow, la plataforma de
generación y maquetación de minutas para audiencias de conciliación y mediaciones legales.

Corre en nuestro propio servidor: por el **secreto profesional**, el audio y el texto de una
audiencia nunca se envían a APIs de terceros.

| | |
|---|---|
| Lenguaje | Python 3.12 |
| Framework | FastAPI + uvicorn |
| Voz a texto | faster-whisper (CTranslate2, int8, CPU) |
| Lenguaje natural | spaCy `es_core_news_sm` + extractores propios |
| Puerto local | **8002** |
| Despliegue | Render (Web Service Docker, plan Free) |

## Lugar en la arquitectura

El motor es la **Capa de IA**: vive por debajo del gateway y no tiene acceso público útil.
Solo el backend le habla, y cada petición va firmada con HMAC-SHA256:

```
timestamp \n MÉTODO \n ruta[?consulta] \n sha256_hex(cuerpo)
```

Cabeceras: `X-ActaFlow-Timestamp` (segundos Unix) y `X-ActaFlow-Signature` (hex). Se rechazan
firmas con más de 300 s de diferencia. Los mismos vectores de prueba se verifican en el BFF,
en el backend y aquí (`tests/unit/test_hmac_firma.py`).

## Endpoints (bloque 0)

| Método y ruta | Firma | Uso |
|---|---|---|
| `GET /health` | No | Chequeo de Render y "despertador" del backend. Informa versión y modelos instalados. |
| `POST /v1/diagnostico/benchmark` | Sí | Mide en el entorno real la memoria pico, el tiempo de carga, el factor de tiempo real y el WER de cada modelo, cada uno en su propio subproceso. |

Errores uniformes: `{"estado": 401, "codigo": "firma_invalida", "mensaje": "..."}`.

## Desarrollo local (PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# Variables (una sola vez; luego cierra por completo VS Code / IntelliJ)
[Environment]::SetEnvironmentVariable("ACTAFLOW_ENGINE_HMAC_SECRET", "<secreto-local-de-32+-caracteres>", "User")
[Environment]::SetEnvironmentVariable("ACTAFLOW_ENGINE_MODELS_DIR", "$PWD\models", "User")

# Opcional: descargar modelos para probar de verdad en local
python -m actaflow_engine.herramientas.descargar_modelos --destino .\models tiny base

uvicorn --factory actaflow_engine.main:create_app --port 8002 --reload
```

Verificación:

```powershell
python -m pytest -q
ruff check src tests
ruff format --check src tests
```

## Docker

```powershell
docker build -t actaflow-ai-engine .
docker run --rm -p 8002:8002 --memory=512m -e ACTAFLOW_ENGINE_HMAC_SECRET=<secreto> actaflow-ai-engine
```

Los modelos (`tiny`, `base`, `small` por defecto; argumento `ASR_MODELOS`) y el modelo de spaCy
se descargan **al construir la imagen**: el disco de Render Free es efímero y se borra al dormir.

## Runbook de despliegue (Render)

1. Render → **New → Web Service** → conectar `dramirezdlp99/actaflow-ai-engine`.
2. Runtime **Docker**, región **Virginia (US East)**, la más cercana a Neon us-east-1, plan **Free**.
3. Health check path: `/health`.
4. Variables de entorno:
   - `ACTAFLOW_ENGINE_HMAC_SECRET` = secreto de producción (el mismo que `ACTAFLOW_ENGINE_HMAC_SECRET` del backend).
   - `ACTAFLOW_ENGINE_ASR_MODEL` = `tiny` (hasta que las mediciones digan otra cosa).
5. Auto-Deploy: **After CI Checks Pass**, rama `main`.

## Mediciones en producción

Con el servicio desplegado:

```powershell
# 1) Arranque en frío: ejecútalo cuando el motor lleve más de 15 min sin tráfico
python scripts\benchmark_remoto.py arranque --url https://<tu-motor>.onrender.com

# 2) Benchmark de modelos (usa el secreto de PRODUCCIÓN del motor)
$env:ACTAFLOW_ENGINE_HMAC_SECRET = "<secreto-de-produccion>"
python scripts\benchmark_remoto.py modelos --url https://<tu-motor>.onrender.com --modelos tiny base small --spacy
```

Los resultados quedan en `mediciones_locales/` (ignorada por Git) y se resumen en
[`docs/mediciones.md`](docs/mediciones.md), que es donde se toma la decisión del modelo.
