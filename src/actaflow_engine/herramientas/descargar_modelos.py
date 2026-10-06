"""Descarga modelos de faster-whisper a una carpeta local.

Se ejecuta durante ``docker build``: el sistema de archivos de Render Free es efimero, asi que
los modelos deben quedar dentro de la imagen y no descargarse en cada arranque.

Uso: python -m actaflow_engine.herramientas.descargar_modelos --destino /models tiny base
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from actaflow_engine.config import MODELOS_ASR_SOPORTADOS
from actaflow_engine.inventario import carpeta_modelo_asr

Descargador = Callable[[str, str], str]


def _descargador_real(nombre: str, destino: str) -> str:
    from faster_whisper import download_model

    return download_model(nombre, output_dir=destino)


def descargar(
    modelos: list[str], destino: Path, descargador: Descargador = _descargador_real
) -> list[Path]:
    invalidos = [m for m in modelos if m not in MODELOS_ASR_SOPORTADOS]
    if invalidos:
        raise ValueError(f"Modelos no soportados: {invalidos}")
    rutas = []
    for nombre in modelos:
        carpeta = carpeta_modelo_asr(destino, nombre)
        carpeta.mkdir(parents=True, exist_ok=True)
        descargador(nombre, str(carpeta))
        if not (carpeta / "model.bin").is_file():
            raise RuntimeError(f"La descarga de {nombre} no dejo model.bin en {carpeta}")
        rutas.append(carpeta)
    return rutas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destino", type=Path, required=True)
    parser.add_argument("modelos", nargs="+")
    args = parser.parse_args(argv)
    for ruta in descargar(args.modelos, args.destino):
        print(f"Modelo listo en {ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
