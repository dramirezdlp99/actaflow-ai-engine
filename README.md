<div align="center">

# 🧠 ActaFlow · Motor de IA

**Voz a texto, extracción de entidades jurídicas y PDF del acta, en nuestro propio servidor.**

*Python 3.12 · gRPC · faster-whisper · spaCy · fpdf2 · Render*

![Python](https://img.shields.io/badge/Python-3.12-1d3557)
![gRPC](https://img.shields.io/badge/gRPC-nativo%20%2B%20gRPC--Web-9b2335)
![Contratos](https://img.shields.io/badge/contratos-v0.4.0-1d3557)
![Pruebas](https://img.shields.io/badge/pruebas-162%20en%20verde-2e7d32)
![Ruff](https://img.shields.io/badge/ruff-limpio-2e7d32)

| | |
|---|---|
| 👨‍💻 **Desarrollado por** | David Fernando Ramírez de la Parra |
| 👨‍🏫 **Profesor** | Jhonatan Andrés Mideros Narváez |
| 📚 **Asignatura** | Programación Orientada a la Web |
| 🏛️ **Institución** | Universidad Cooperativa de Colombia |

</div>

---

## 🧭 ¿Qué es ActaFlow?

ActaFlow es una **plataforma web para generar y maquetar minutas y actas de audiencias de conciliación y mediación**
(caso de estudio 3). Mientras la audiencia ocurre, el sistema graba cada intervención, la transcribe, extrae las
entidades jurídicas y, con lo que una persona revisa, llena la plantilla del acta. Al final genera el **PDF sellado**,
que las partes aceptan con su segundo factor y que cualquiera puede verificar.

| Repositorio | Qué es |
|---|---|
| 📜 [actaflow-contracts](https://github.com/dramirezdlp99/actaflow-contracts) | La API (Contract-First) |
| 🖥️ [actaflow-frontend](https://github.com/dramirezdlp99/actaflow-frontend) | Interfaz web y BFF |
| ⚙️ [actaflow-backend](https://github.com/dramirezdlp99/actaflow-backend) | Microservicios de identidad y expedientes |
| 🧠 **actaflow-ai-engine** (este) | El motor de IA |

---

## 🤖 La IA, co-protagonista del caso de estudio

El caso pide **procesamiento de lenguaje natural e ingesta de voz a texto con extracción de entidades nombradas en el
servidor**. Así se cumple cada paso del flujo:

| Paso del caso de estudio (3.3) | Cómo lo hace ActaFlow |
|---|---|
| 1. Capturar el audio de las intervenciones | El navegador graba y corta cada intervención en las pausas, y la **sella para el motor** antes de enviarla |
| 2. Transcribir e identificar a cada hablante | **faster-whisper** transcribe cada intervención. El hablante lo marca la sala y viaja sellado con el audio |
| 3. Extraer las entidades jurídicas clave | **spaCy + extractores propios**: partes con su documento, montos, fechas límite de pago, compromisos y cláusulas penales |
| 4. Autocompletar la minuta y dejarla lista para firma | Lo revisado llena la plantilla en el navegador; el motor genera el **PDF** y legal-case lo **sella** |

> 🔒 **Por el secreto profesional, el audio y el texto de una audiencia nunca se envían a APIs de terceros.** Todo
> corre con modelos locales y gratuitos dentro de este servicio.

---

## 📐 Contratos primero

El motor no define su API: **la implementa**. Los servicios, mensajes y reglas están en
[actaflow-contracts](https://github.com/dramirezdlp99/actaflow-contracts). Aquí se copia una versión fijada (v0.4.0)
y de ella se genera el código:

```
contracts/                 copia fiel de actaflow-contracts (versión en contracts.lock.json)
src/actaflow/...           código GENERADO (mensajes *_pb2 y servicios *_pb2_grpc)
src/buf/validate/...       código GENERADO de protovalidate
src/actaflow_engine/
  rpc/                     servidor gRPC, servicios, interceptor de firma y pasarela gRPC-Web
  voz/                     carga y uso de faster-whisper
  extraccion/              extractores de entidades (números, fechas, documentos)
  documentos/              PDF del acta (fpdf2)
  seguridad/               firma HMAC y apertura de sobres sellados
  diagnostico/             benchmark de modelos en el entorno real
```

| Servicio | Qué hace |
|---|---|
| `actaflow.system.v1.ServiceStatusService` | Estado de los modelos y transporte por el que llegó la llamada |
| `actaflow.engine.v1.EngineDiagnosticsService` | Benchmark de modelos en el entorno real |
| `actaflow.engine.v1.TranscriptionService` | Transcripción de intervenciones selladas, y en vivo por streaming |
| `actaflow.engine.v1.ExtractionService` | Las cinco familias de entidades jurídicas, sobre contenido sellado |
| `actaflow.engine.v1.DocumentService` | PDF del acta final a partir del contenido sellado |
| `actaflow.crypto.v1.ProcessorKeyService` | Clave pública ECDH P-256 del motor |

---

## 🔐 Contenido sellado para el motor

El motor **nunca recibe audio ni texto en claro por la red**:

1. El navegador genera una **clave de contenido K** y cifra la entrada con K (AES-256-GCM).
2. Envuelve K para la **clave pública del motor** (ECDH P-256 → HKDF-SHA-256 → AES-256-GCM).
3. Aparte, cifra K con la **clave del caso**, para que los participantes puedan abrir el resultado.
4. legal-case-service solo reenvía esos bytes: no puede abrir nada.
5. El motor desenvuelve K **en memoria**, procesa y cifra el resultado con la misma K.

El dato autenticado (AAD), que nunca se transmite, ata cada cifrado a su propósito, su caso y su recurso:
`actaflow/v1|<propósito>|<case_id>|<resource_id>`. Un sobre no se puede reutilizar en otro lugar.

La clave privada del motor va en `ACTAFLOW_ENGINE_PROCESSOR_PRIVATE_KEY` (obligatoria en producción y distinta en
local):

```powershell
python -m actaflow_engine.herramientas.clave_procesador
```

---

## 🎙️ Transcripción

- **`TranscribeSegment`** (el camino de producción; unario, funciona por gRPC-Web): una intervención de hasta 30 s,
  en WAV PCM de 16 kHz (lo que arma el Web Worker del navegador) u Ogg Opus. Los nombres de los participantes viajan
  **sellados con el audio** como pistas para el modelo. Devuelve un `TranscriptionResult` cifrado con la misma clave,
  con el hablante, la confianza de cada tramo y el factor de tiempo real.
- **`StreamTranscription`** (gRPC nativo HTTP/2, local y CI): sesiones de hasta 30 s. Envía un parcial cada ~3 s de
  audio nuevo y el resultado final al cerrar.
- **faster-whisper** en CPU con int8. El modelo se carga una vez, en la primera transcripción, y las transcripciones
  van de una en una (Render Free: una CPU y 512 MB).

### 📊 Decidido con mediciones, no con suposiciones

Medido en Render con `scripts/benchmark_remoto.py` (detalle en [`docs/mediciones.md`](docs/mediciones.md)):

| Modelo | Memoria pico | Factor de tiempo real | ¿Entra en Render Free? |
|---|---|---|---|
| **tiny** + spaCy | **329 MB** | **0,62** (más rápido que el tiempo real) | ✅ **Producción** |
| base + spaCy | 473 MB | 1,88 | ❌ Roza los 512 MB (sirve en local) |
| small | > 512 MB | — | ❌ Render reinició el servicio |

Como la precisión de `tiny` es limitada, la **revisión humana es obligatoria**: la IA propone y una persona confirma
o corrige antes de que algo llegue al acta.

---

## 🔎 Extracción de entidades jurídicas

Reglas deterministas en `extraccion/`. Son explicables, no dependen de servicios externos, y cada entidad lleva su
fragmento de origen, su confianza y si requiere confirmación.

| Familia | Qué reconoce |
|---|---|
| 👤 **Partes** | Personas con cédula de ciudadanía o extranjería o pasaporte; empresas con NIT y dígito de verificación (módulo 11 de la DIAN); su rol (convocante, convocado, apoderado…) y el enlace con los participantes del caso |
| 💰 **Montos** | `$1.500.000`, `1.500.000 pesos`, `2 millones de pesos`, "un millón quinientos mil pesos"; cuotas y valor de cada cuota; quién paga y quién recibe |
| 📅 **Plazos de pago** | Fechas ("15 de noviembre de 2026", "el primero de diciembre", `15/11/2026`) y plazos relativos ("dentro de los treinta días hábiles"), con días hábiles según los festivos de Colombia (Ley 51 de 1983) |
| 📦 **Compromisos de entrega** | "entregará / restituirá / devolverá…", con su obligado y su fecha |
| ⚖️ **Cláusulas penales** | Multa fija, porcentaje e intereses de mora, con su condición ("en caso de…") |

---

## 📄 Acta en PDF

`DocumentService.RenderMinutePdf` hace del motor el **procesador de documentos** del acta final (ADR 0004 de los
contratos):

1. El navegador llena la plantilla y **sella el contenido final** (`FinalContent`: título y HTML) para el motor.
   AAD: `actaflow/v1|minute-final|<caso>|<acta>`.
2. El motor lo abre en memoria y arma el PDF con **fpdf2** (puro Python, sin tocar el disco): tamaño carta,
   encabezado con el título y pie con el número de página.
3. El HTML se vuelve a filtrar: solo `h2`, `h3`, `p`, `br` y `strong`. Un dato que falta sale entre corchetes.
4. Devuelve el **PDF cifrado** con la misma clave (AAD `minute-pdf`) y su **SHA-256**. legal-case firma ese hash
   (sello CMS) **sin ver el documento**.
5. Tope de 200 páginas, para cuidar la memoria de Render Free.

---

## 🛰️ Dos transportes, el mismo código

| Transporte | Dónde | Por qué |
|---|---|---|
| **gRPC nativo (HTTP/2)** en `ACTAFLOW_ENGINE_GRPC_BIND` (por defecto `127.0.0.1:8102`) | Local, CI | Incluye reflexión: `grpcurl` o `buf curl` lo exploran |
| **gRPC-Web (HTTP/1.1)** en el puerto web (8002) | Producción | Render Free solo expone HTTP/1.1; la pasarela reenvía al servidor nativo del mismo contenedor |

Cada llamada pasa por un **interceptor** que:

1. 🔏 Verifica la **firma HMAC-SHA256** de los metadatos sobre los bytes protobuf exactos de la petición:
   `timestamp\nRPC\n/<Servicio>/<Metodo>\nsha256(mensaje)`. Sin firma válida, el servicio ni se ejecuta.
2. ✅ Valida el mensaje con las **reglas del contrato** (protovalidate). Si falla, responde `INVALID_ARGUMENT` con los
   campos incumplidos tipados (`FieldViolations`).

`GET /health` existe solo porque Render lo usa para saber si el contenedor está vivo.

---

## 🧱 El motor dentro de la arquitectura de capas

```
Cliente (navegador) → Borde (BFF Next.js, firma HMAC) → Aplicación (legal-case) → Asíncrona (cola de trabajos)
                                                                                         │
                                                                     Capa de IA  ◄───────┘  ← este servicio
                                                                         │
                                                                   Capa de datos (Neon)
```

El motor está **detrás** de todas las demás capas: el navegador nunca lo llama directamente, solo legal-case, con su
propio secreto HMAC y desde su cola asíncrona. Las llamadas al motor nunca bloquean a quien está usando la app.

---

## 🛠️ Desarrollo local (PowerShell)

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
python -m pytest -q                       # 162 pruebas
ruff check src tests scripts
ruff format --check src tests scripts
```

Actualizar a una versión nueva del contrato:

```powershell
node scripts\contracts.mjs sync v0.4.0
python scripts\generar_contratos.py
```

---

## 🚀 Docker y despliegue (Render)

```powershell
docker build -t actaflow-ai-engine .
docker run --rm -p 8002:8002 --memory=512m -e ACTAFLOW_ENGINE_HMAC_SECRET=<secreto> actaflow-ai-engine
```

Los modelos (tiny, base, small; argumento `ASR_MODELOS`) y spaCy se descargan **al construir la imagen**, porque el
disco de Render Free es efímero.

**Render:** Web Service Docker, región Virginia, plan Free, health check `/health`. Variables:
`ACTAFLOW_ENGINE_HMAC_SECRET`, `ACTAFLOW_ENGINE_PROCESSOR_PRIVATE_KEY` y `ACTAFLOW_ENGINE_ASR_MODEL=tiny`.
Despliegue manual después del CI en verde: **Manual Deploy → Deploy latest commit**.

> 🔑 Todos los secretos van por variables de entorno, nunca en el código ni en el historial, y son distintos en local
> y en producción.

### 📏 Mediciones

```powershell
python scripts\benchmark_remoto.py arranque --url https://<motor>.onrender.com
$env:ACTAFLOW_ENGINE_HMAC_SECRET = "<secreto-de-produccion>"
python scripts\benchmark_remoto.py modelos --url https://<motor>.onrender.com --modelos tiny base --spacy
```

---

## 🧪 Calidad

- **162 pruebas** (pytest): extractores, festivos y días hábiles, sobres sellados, interceptor de firma, los dos
  transportes, transcripción, extracción y PDF de punta a punta por gRPC.
- **ruff** (lint y formato) limpio.
- CI en cada push: contratos idénticos a la versión publicada, código generado al día, pruebas y ruff.

---

<div align="center">

**ActaFlow** · Proyecto académico de Ingeniería de Software · Sin datos reales de personas ni de procesos

Desarrollado por **David Fernando Ramírez de la Parra** · Profesor **Jhonatan Andrés Mideros Narváez**<br>
**Programación Orientada a la Web** · **Universidad Cooperativa de Colombia**

</div>
