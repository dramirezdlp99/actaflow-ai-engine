# ActaFlow · Motor de IA

Microservicio de **voz a texto** y **extracción de entidades jurídicas** de ActaFlow, la
plataforma de generación y maquetación de minutas para audiencias de conciliación y
mediaciones legales.

Corre en nuestro propio servidor: por el **secreto profesional**, el audio y el texto de una
audiencia nunca se envían a APIs de terceros.

| | |
|---|---|
| Lenguaje | Python 3.12 |
| Comunicación | **gRPC** (Protocol Buffers), contratos en [`actaflow-contracts`](https://github.com/dramirezdlp99/actaflow-contracts) |
| Voz a texto | faster-whisper (CTranslate2, int8, CPU) |
| Lenguaje natural | spaCy `es_core_news_sm` + extractores propios |
| Puertos locales | **8002** (web: gRPC-Web y `/health`) · **8102** (gRPC nativo, HTTP/2) |
| Despliegue | Render (Web Service Docker, plan Free) |

## Contratos primero

El motor no define su API: la implementa. Los servicios, mensajes y reglas están en el repo
de contratos. Aquí se copia una versión fijada, y de ella se genera el código:

```
contracts/                 copia fiel de actaflow-contracts (versión en contracts.lock.json)
src/actaflow/...           código generado (mensajes *_pb2 y servicios *_pb2_grpc)
src/buf/validate/...       código generado de protovalidate
src/actaflow_engine/rpc/   lo que escribimos: servidor, servicios, interceptor, pasarela
```

Servicios que implementa hoy:

| Servicio | Estado |
|---|---|
| `actaflow.system.v1.ServiceStatusService` | Implementado: estado de los modelos y transporte usado |
| `actaflow.engine.v1.EngineDiagnosticsService` | Implementado: benchmark de modelos en el entorno real |
| `actaflow.engine.v1.TranscriptionService` | Contrato listo; responde `UNIMPLEMENTED` hasta el bloque IA-6 |
| `actaflow.engine.v1.ExtractionService` | Contrato listo; extractores en los bloques IA-2 a IA-5 |
| `actaflow.crypto.v1.ProcessorKeyService` | Contrato listo; llega con el audio sellado (IA-6) |

## Dos transportes, el mismo código

- **gRPC nativo (HTTP/2)** en `ACTAFLOW_ENGINE_GRPC_BIND` (por defecto `127.0.0.1:8102`):
  local, CI y redes con HTTP/2. Incluye reflexión, así que `grpcurl` o `buf curl` pueden
  explorarlo.
- **gRPC-Web (HTTP/1.1)** en el puerto web: es el que se usa en producción, porque Render Free
  solo expone HTTP/1.1. La pasarela desarma las tramas y reenvía la llamada al servidor nativo
  del mismo contenedor, así que la firma, la validación y los servicios son idénticos por los
  dos caminos.

Cada llamada pasa por un interceptor que:

1. verifica la **firma HMAC** de los metadatos sobre los **bytes protobuf exactos** de la
   petición (`timestamp\nRPC\n/<Servicio>/<Metodo>\nsha256(mensaje)`);
2. valida el mensaje con las **reglas del contrato** (protovalidate). Si falla, responde
   `INVALID_ARGUMENT` con los campos incumplidos tipados (`actaflow.common.v1.FieldViolations`).

`GET /health` sigue existiendo solo porque Render lo usa para saber si el contenedor está vivo.

## Desarrollo local (PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn --factory actaflow_engine.main:create_app --port 8002
```

Verificación:

```powershell
node scripts\contracts.mjs check          # contracts/ coincide con la versión fijada
python scripts\generar_contratos.py --check
python -m pytest -q
ruff check src tests scripts
ruff format --check src tests scripts
```

Actualizar a una versión nueva del contrato:

```powershell
node scripts\contracts.mjs sync v0.2.0
python scripts\generar_contratos.py
```

## Docker y despliegue (Render)

```powershell
docker build -t actaflow-ai-engine .
docker run --rm -p 8002:8002 --memory=512m -e ACTAFLOW_ENGINE_HMAC_SECRET=<secreto> actaflow-ai-engine
```

Los modelos (`tiny`, `base`, `small`; argumento `ASR_MODELOS`) y spaCy se descargan **al
construir la imagen**: el disco de Render Free es efímero.

Render: Web Service Docker, región Virginia, plan Free, health check `/health`, variables
`ACTAFLOW_ENGINE_HMAC_SECRET` y `ACTAFLOW_ENGINE_ASR_MODEL=tiny`, auto-deploy tras el CI.

## Mediciones

```powershell
python scripts\benchmark_remoto.py arranque --url https://<motor>.onrender.com
$env:ACTAFLOW_ENGINE_HMAC_SECRET = "<secreto-de-produccion>"
python scripts\benchmark_remoto.py modelos --url https://<motor>.onrender.com --modelos tiny base --spacy
```

Resultados y decisión del modelo: [`docs/mediciones.md`](docs/mediciones.md).
