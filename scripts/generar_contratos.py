"""Genera el codigo Python de los contratos que usa el motor.

Fuente: la carpeta contracts/ (copia fijada de actaflow-contracts, ver contracts.lock.json).
Destino: src/actaflow/... y src/buf/validate/... (codigo generado, se versiona en Git).

    python scripts/generar_contratos.py           regenera
    python scripts/generar_contratos.py --check   falla si lo versionado no coincide (CI)

Usa grpcio-tools (protoc embebido), con la version fijada en pyproject.toml, para que el
resultado sea identico en cualquier maquina.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from grpc_tools import protoc

RAIZ = Path(__file__).resolve().parents[1]
CONTRATOS = RAIZ / "contracts"
SALIDA = RAIZ / "src"
CARPETAS_GENERADAS = ("actaflow", "buf")

# Solo mensajes.
MENSAJES = [
    "buf/validate/validate.proto",
    "actaflow/common/v1/values.proto",
    "actaflow/common/v1/errors.proto",
    "actaflow/common/v1/pagination.proto",
    "actaflow/legal/v1/transcript.proto",
    "actaflow/legal/v1/entities.proto",
    "actaflow/minutes/v1/minute.proto",
]
# Mensajes y servicios gRPC (el motor implementa estos servicios).
SERVICIOS = [
    "actaflow/crypto/v1/crypto.proto",
    "actaflow/system/v1/service_status.proto",
    "actaflow/engine/v1/engine.proto",
]


def _protoc(argumentos: list[str]) -> None:
    incluir_wkt = str(Path(protoc.__file__).parent / "_proto")
    codigo = protoc.main(["grpc_tools.protoc", f"-I{CONTRATOS}", f"-I{incluir_wkt}", *argumentos])
    if codigo != 0:
        raise SystemExit(f"protoc fallo con codigo {codigo}")


def generar(destino: Path) -> None:
    for carpeta in CARPETAS_GENERADAS:
        shutil.rmtree(destino / carpeta, ignore_errors=True)
    _protoc([f"--python_out={destino}", f"--pyi_out={destino}", *MENSAJES])
    _protoc(
        [
            f"--python_out={destino}",
            f"--pyi_out={destino}",
            f"--grpc_python_out={destino}",
            *SERVICIOS,
        ]
    )


def _archivos(raiz: Path) -> dict[str, bytes]:
    resultado = {}
    for carpeta in CARPETAS_GENERADAS:
        for ruta in sorted((raiz / carpeta).rglob("*")):
            if ruta.is_file() and "__pycache__" not in ruta.parts:
                relativo = ruta.relative_to(raiz).as_posix()
                resultado[relativo] = ruta.read_bytes().replace(b"\r\n", b"\n")
    return resultado


def comprobar() -> list[str]:
    with tempfile.TemporaryDirectory() as temporal:
        generar(Path(temporal))
        esperado = _archivos(Path(temporal))
    actual = _archivos(SALIDA)
    problemas = [f"falta {r}" for r in esperado if r not in actual]
    problemas += [
        f"desactualizado {r}" for r in esperado if r in actual and actual[r] != esperado[r]
    ]
    problemas += [f"sobra {r}" for r in actual if r not in esperado]
    return problemas


def main(argumentos: list[str]) -> int:
    if "--check" in argumentos:
        problemas = comprobar()
        if problemas:
            print("El codigo generado no coincide con contracts/:\n  " + "\n  ".join(problemas))
            print("Ejecuta: python scripts/generar_contratos.py")
            return 1
        print("Codigo generado al dia con contracts/")
        return 0
    generar(SALIDA)
    print(f"Codigo generado en {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
