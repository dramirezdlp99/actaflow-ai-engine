# Mediciones del motor en producción

Las decisiones del motor se toman con datos medidos en Render, no con suposiciones.
Fuente: `scripts/benchmark_remoto.py`, ejecutado el 6 de octubre de 2026 contra
`https://actaflow-ai-engine.onrender.com`.

## Entorno medido

| Dato | Valor medido | Fuente |
|---|---|---|
| Límite de memoria del contenedor | **512 MB** (536 870 912 bytes) | `memory.max` (cgroup v2) |
| Cuota de CPU | **0,15 núcleos** (las fuentes externas decían 0,1) | `cpu.max` (cgroup v2) |
| CPU visibles para el proceso | 8 (solo se puede usar el 15 % de una) | `os.cpu_count()` |
| Arranque en frío del motor (hasta el primer 200 en `/health`) | **32,9 s** | `benchmark_remoto.py arranque` |
| Arranque en frío del backend | pendiente (la medición salió con el servicio ya despierto: 0,6 s) | `benchmark_remoto.py arranque` |

## Modelos de voz a texto

Audio: guion de `src/actaflow_engine/diagnostico/muestras/guion_es.txt` (34,6 s), sintetizado con
espeak-ng. Configuración: int8, 1 hilo, `beam_size=1`, `language="es"`, VAD activado.

| Modelo | Estado | Carga (s) | Transcripción (s) | Factor de tiempo real | Memoria pico (MB) | WER |
|---|---|---|---|---|---|---|
| tiny | ok | 1,8 | 21,0 | **0,61** | 307 | 0,68 |
| tiny + spaCy `sm` | ok | 1,8 (+2,8 spaCy) | 21,6 | **0,62** | **329** | 0,69 |
| base + spaCy `sm` | ok | 3,3 (+3,2 spaCy) | 65,2 | 1,88 | 473 | 0,43 |
| small | **sin memoria** | — | — | — | > 512 (Render reinició el servicio) | — |

La memoria pico es la del subproceso de medición. El proceso principal de uvicorn suma unos
60–80 MB más, que también cuentan contra los 512 MB.

## Criterio de decisión

Se elige el modelo más grande que cumpla **las dos** condiciones:

1. Memoria pico con spaCy cargado ≤ 380 MB (deja margen frente a 512 MB).
2. Factor de tiempo real ≤ 3 (una intervención de 20 s lista en un minuto o menos).

| Modelo | Memoria ≤ 380 MB | Tiempo real ≤ 3 | ¿Cumple? |
|---|---|---|---|
| tiny | Sí (329 MB) | Sí (0,62) | **Sí** |
| base | No (473 MB; con uvicorn rozaría los 512 MB) | Sí (1,88) | No |
| small | No (no carga) | — | No |

## Decisión

- **Producción (Render Free): `tiny`.** Es el único que entra con margen de memoria. Es **más
  rápido que el tiempo real** (0,62): una intervención de 20 s queda transcrita en unos 12 s. El
  diseño de transcripción por intervención en la cola asíncrona funciona holgado.
- **Local y demostraciones con más recursos: `base`.** Reduce el WER de 0,68 a 0,43 con este audio.
  Se elige con `ACTAFLOW_ENGINE_ASR_MODEL=base`.
- **`small` queda descartado en el plan gratuito.**

## Advertencia honesta sobre la precisión

Un WER de 0,68 es alto, pero esta medición **subestima** la precisión real. La voz de espeak-ng
es robótica y sin entonación, y Whisper está entrenado con voz humana. Los errores típicos
("Paso" por "Pasto", "frinta" por "treinta") vienen sobre todo de esa voz sintética.

Mitigaciones previstas, que se medirán con el mismo guion:

1. **Audio humano:** grabar el guion con nuestra voz y repetir la medición (kit de pruebas).
2. **`initial_prompt` con el contexto del expediente:** nombres de las partes, ciudad y
   vocabulario jurídico ("conciliación", "convocante", "cuotas", "cláusula penal").
3. **Revisión humana obligatoria:** la transcripción y las entidades son propuestas que el
   abogado corrige antes de volcarlas en la minuta. Nunca se firma sin revisión.
4. **Extracción tolerante:** los extractores de montos y fechas aceptan variantes y marcan con
   baja confianza lo dudoso.
