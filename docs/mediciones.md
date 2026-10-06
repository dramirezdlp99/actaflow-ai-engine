# Mediciones del motor en producción

Las decisiones del motor se toman con datos medidos en Render, no con suposiciones.
Este archivo se completa con la salida de `scripts/benchmark_remoto.py`.

## Entorno medido

| Dato | Valor medido | Fuente |
|---|---|---|
| Límite de memoria del contenedor | _pendiente_ | `memory.max` (cgroup v2) |
| Cuota de CPU (núcleos) | _pendiente_ | `cpu.max` (cgroup v2) |
| Arranque en frío del motor (hasta el primer 200 en `/health`) | _pendiente_ | `benchmark_remoto.py arranque` |
| Arranque en frío del backend | _pendiente_ | `benchmark_remoto.py arranque` contra `/actuator/health` |

## Modelos de voz a texto

Audio: guion de `src/actaflow_engine/diagnostico/muestras/guion_es.txt` (unos 30 s),
sintetizado con espeak-ng y, después, leído por nosotros.

| Modelo | Estado | Carga (s) | Transcripción (s) | Factor de tiempo real | Memoria pico (MB) | WER |
|---|---|---|---|---|---|---|
| tiny | _pendiente_ | | | | | |
| base | _pendiente_ | | | | | |
| small | _pendiente_ | | | | | |

## Criterio de decisión

Se elige el modelo más grande que cumpla **las dos** condiciones:

1. Memoria pico con spaCy cargado ≤ 380 MB (deja margen frente a 512 MB).
2. Factor de tiempo real ≤ 3 (una intervención de 20 s lista en un minuto o menos).

Si ninguno cumple la segunda, se mantiene `tiny` y la transcripción por intervención en la
cola asíncrona, y se documenta aquí la latencia real que verá el usuario.

## Decisión

_pendiente de las mediciones del bloque 0_
