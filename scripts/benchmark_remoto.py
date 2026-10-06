"""Mide el motor desplegado (Render) desde tu computador.

Dos modos:

1. Arranque en frio: espera la respuesta de /health y mide cuanto tarda el primer 200.
   Ejecutalo cuando el servicio lleve mas de 15 minutos sin trafico (dormido).

     python scripts/benchmark_remoto.py arranque --url https://actaflow-ai-engine.onrender.com

2. Benchmark de modelos: llama a POST /v1/diagnostico/benchmark firmado con HMAC.

     python scripts/benchmark_remoto.py modelos --url https://... --modelos tiny base small --spacy

El secreto se lee de la variable de entorno ACTAFLOW_ENGINE_HMAC_SECRET (el de produccion).
Los resultados se guardan como JSON en mediciones_locales/ para copiarlos a docs/mediciones.md.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from actaflow_engine.seguridad.hmac_firma import cabeceras_firmadas  # noqa: E402

CARPETA_SALIDA = Path(__file__).resolve().parents[1] / "mediciones_locales"


def _guardar(nombre: str, datos: dict[str, object]) -> Path:
    CARPETA_SALIDA.mkdir(exist_ok=True)
    marca = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    ruta = CARPETA_SALIDA / f"{nombre}-{marca}.json"
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
    return ruta


def medir_arranque(url: str, limite_s: int) -> int:
    inicio = time.perf_counter()
    intentos = 0
    while time.perf_counter() - inicio < limite_s:
        intentos += 1
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=90) as resp:
                if resp.status == 200:
                    cuerpo = json.loads(resp.read())
                    datos = {
                        "segundos_hasta_200": round(time.perf_counter() - inicio, 2),
                        "intentos": intentos,
                        "health": cuerpo,
                    }
                    print(json.dumps(datos, indent=2, ensure_ascii=False))
                    print(f"Guardado en {_guardar('arranque', datos)}")
                    return 0
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"Intento {intentos}: aun no responde ({exc})")
        time.sleep(3)
    print(f"No respondio en {limite_s} s")
    return 1


def medir_modelos(url: str, modelos: list[str], con_spacy: bool) -> int:
    secreto = os.environ.get("ACTAFLOW_ENGINE_HMAC_SECRET", "")
    if len(secreto) < 32:
        print("Define ACTAFLOW_ENGINE_HMAC_SECRET (el secreto de produccion del motor).")
        return 2
    ruta = "/v1/diagnostico/benchmark"
    cuerpo = json.dumps({"modelos": modelos, "con_spacy": con_spacy}).encode()
    cabeceras = {"Content-Type": "application/json"}
    cabeceras.update(cabeceras_firmadas(secreto, "POST", ruta, cuerpo))
    peticion = urllib.request.Request(f"{url}{ruta}", data=cuerpo, headers=cabeceras, method="POST")
    try:
        with urllib.request.urlopen(peticion, timeout=1800) as resp:
            datos = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode(errors='replace')}")
        return 1
    print(json.dumps(datos, indent=2, ensure_ascii=False))
    print(f"Guardado en {_guardar('benchmark', datos)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="modo", required=True)
    arranque = sub.add_parser("arranque")
    arranque.add_argument("--url", required=True)
    arranque.add_argument("--limite", type=int, default=300)
    modelos = sub.add_parser("modelos")
    modelos.add_argument("--url", required=True)
    modelos.add_argument("--modelos", nargs="+", default=["tiny", "base", "small"])
    modelos.add_argument("--spacy", action="store_true")
    args = parser.parse_args()
    url = args.url.rstrip("/")
    if args.modo == "arranque":
        return medir_arranque(url, args.limite)
    return medir_modelos(url, args.modelos, args.spacy)


if __name__ == "__main__":
    sys.exit(main())
