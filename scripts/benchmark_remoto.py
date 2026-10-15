"""Mide el motor desplegado (Render) desde tu computador.

Dos modos:

1. Arranque en frio: espera la respuesta de /health y mide cuanto tarda el primer 200.
   Ejecutalo cuando el servicio lleve mas de 15 minutos sin trafico (dormido).

     python scripts/benchmark_remoto.py arranque --url https://actaflow-ai-engine.onrender.com

2. Benchmark de modelos: llama a actaflow.engine.v1.EngineDiagnosticsService/RunBenchmark por
   gRPC-Web, firmado con HMAC (el mismo camino que usa legal-case-service en produccion).

     python scripts/benchmark_remoto.py modelos --url https://... --modelos tiny base --spacy

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

from google.protobuf.json_format import MessageToDict  # noqa: E402

from actaflow.engine.v1 import engine_pb2  # noqa: E402
from actaflow_engine.rpc.cliente_web import GrpcWebError, llamar  # noqa: E402

CARPETA_SALIDA = Path(__file__).resolve().parents[1] / "mediciones_locales"
METODO = "/actaflow.engine.v1.EngineDiagnosticsService/RunBenchmark"
MODELOS = {
    "tiny": engine_pb2.MODEL_SIZE_TINY,
    "base": engine_pb2.MODEL_SIZE_BASE,
    "small": engine_pb2.MODEL_SIZE_SMALL,
}


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
                    datos = {
                        "segundos_hasta_200": round(time.perf_counter() - inicio, 2),
                        "intentos": intentos,
                        "health": json.loads(resp.read()),
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
    peticion = engine_pb2.RunBenchmarkRequest(
        models=[MODELOS[m] for m in modelos], include_nlp=con_spacy
    )
    try:
        respuesta = llamar(
            url, METODO, peticion, engine_pb2.RunBenchmarkResponse, secreto, timeout_s=1800
        )
    except GrpcWebError as exc:
        print(f"Error {exc}")
        return 1
    datos = MessageToDict(respuesta, preserving_proto_field_name=True)
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
    modelos.add_argument("--modelos", nargs="+", choices=sorted(MODELOS), default=["tiny"])
    modelos.add_argument("--spacy", action="store_true")
    args = parser.parse_args()
    url = args.url.rstrip("/")
    if args.modo == "arranque":
        return medir_arranque(url, args.limite)
    return medir_modelos(url, args.modelos, args.spacy)


if __name__ == "__main__":
    sys.exit(main())
