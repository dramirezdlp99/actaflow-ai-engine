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
| `actaflow.engine.v1.ExtractionService` | Implementado (IA-3): las cinco familias de entidades, sobre contenido sellado |
| `actaflow.crypto.v1.ProcessorKeyService` | Implementado (IA-3): clave pública ECDH P-256 del motor |

## Contenido sellado para el motor (IA-3)

El motor nunca recibe la transcripción en claro por la red. El navegador genera una clave de
contenido K, cifra la entrada con K y envuelve K para la **clave pública del motor**
(`ProcessorKeyService`), con el mismo esquema que las claves de los casos (ECDH P-256 → HKDF-SHA-256
→ AES-256-GCM). legal-case-service solo reenvía bytes cifrados. El motor desenvuelve K en memoria,
procesa y cifra el resultado con la misma K, que los participantes abren con la clave del caso.
El AAD, que nunca se transmite, es `actaflow/v1|<propósito>|<case_id>|<resource_id>`.

La clave privada del motor va en `ACTAFLOW_ENGINE_PROCESSOR_PRIVATE_KEY` (obligatoria en
producción, distinta en local):

```powershell
python -m actaflow_engine.herramientas.clave_procesador
```

## Extracción de entidades (IA-3)

Reglas deterministas en `extraccion/`: son explicables, no dependen de servicios externos y cada
entidad lleva su fragmento de origen, su confianza y si requiere confirmación.

| Familia | Qué reconoce |
|---|---|
| Partes | Personas con cédula de ciudadanía o extranjería o pasaporte; empresas con NIT y dígito de verificación (módulo 11 de la DIAN); rol (convocante, convocado, apoderado…); enlace con los participantes del caso |
| Montos | `$1.500.000`, `1.500.000 pesos`, `2 millones de pesos`, "un millón quinientos mil pesos"; cuotas y valor de cada cuota; quién paga y quién recibe |
| Plazos de pago | Fechas ("15 de noviembre de 2026", "el primero de diciembre", `15/11/2026`) y plazos relativos ("dentro de los treinta días hábiles"), con días hábiles según los festivos de Colombia (Ley 51 de 1983) |
| Compromisos de entrega | "entregará / restituirá / devolverá …", con su obligado y su fecha |
| Cláusulas penales | Multa fija, porcentaje e intereses de mora, con su condición ("en caso de …") |

Cada línea del texto de entrada es un segmento de la transcripción (`segment_index`).

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
