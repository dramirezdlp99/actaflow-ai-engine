"""Benchmark de modelos de voz a texto en el entorno real (por ejemplo, Render Free).

Cada modelo se mide en su propio subproceso (ver ``medir.py``). Si el contenedor se queda
sin memoria, el sistema mata ese subproceso (SIGKILL) y aqui se informa como ``oom`` en lugar
de tumbar el motor.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from actaflow_engine.diagnostico.entorno import EntornoContenedor, leer_entorno
from actaflow_engine.diagnostico.wer import wer
from actaflow_engine.inventario import carpeta_modelo_asr

CODIGOS_SIGKILL = {-9, 137}


class EstadoMedicion(StrEnum):
    OK = "ok"
    OOM = "oom"
    TIMEOUT = "timeout"
    ERROR = "error"
    NO_INSTALADO = "no_instalado"


class ProcesoTerminado(Protocol):
    returncode: int
    stdout: str
    stderr: str


Ejecutor = Callable[[list[str], int], ProcesoTerminado]


def ejecutor_subproceso(comando: list[str], timeout_s: int) -> ProcesoTerminado:
    return subprocess.run(  # noqa: S603 - comando construido internamente, sin shell
        comando, capture_output=True, text=True, timeout=timeout_s, check=False
    )


@dataclass
class ResultadoModelo:
    modelo: str
    estado: EstadoMedicion
    detalle: str | None = None
    metricas: dict[str, object] = field(default_factory=dict)
    wer: float | None = None


@dataclass
class InformeBenchmark:
    entorno: EntornoContenedor
    audio: str
    resultados: list[ResultadoModelo]

    def como_dict(self) -> dict[str, object]:
        return {
            "entorno": self.entorno.como_dict(),
            "audio": self.audio,
            "resultados": [asdict(r) for r in self.resultados],
        }


def construir_comando(modelo_dir: Path, audio: Path, spacy_modelo: str | None) -> list[str]:
    comando = [
        sys.executable,
        "-m",
        "actaflow_engine.diagnostico.medir",
        "--modelo-dir",
        str(modelo_dir),
        "--audio",
        str(audio),
    ]
    if spacy_modelo:
        comando += ["--spacy", spacy_modelo]
    return comando


def _ultimas_lineas(texto: str, n: int = 5) -> str:
    return "\n".join(texto.strip().splitlines()[-n:])


def medir_modelo(
    nombre: str,
    models_dir: Path,
    audio: Path,
    referencia: str | None,
    timeout_s: int,
    spacy_modelo: str | None,
    ejecutor: Ejecutor,
) -> ResultadoModelo:
    modelo_dir = carpeta_modelo_asr(models_dir, nombre)
    if not (modelo_dir / "model.bin").is_file():
        return ResultadoModelo(nombre, EstadoMedicion.NO_INSTALADO, f"No existe {modelo_dir}")
    try:
        proceso = ejecutor(construir_comando(modelo_dir, audio, spacy_modelo), timeout_s)
    except subprocess.TimeoutExpired:
        return ResultadoModelo(nombre, EstadoMedicion.TIMEOUT, f"Supero {timeout_s} s")

    if proceso.returncode in CODIGOS_SIGKILL:
        return ResultadoModelo(
            nombre, EstadoMedicion.OOM, "El sistema mato el proceso (memoria insuficiente)"
        )
    if proceso.returncode != 0:
        return ResultadoModelo(nombre, EstadoMedicion.ERROR, _ultimas_lineas(proceso.stderr))
    try:
        metricas = json.loads(proceso.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return ResultadoModelo(nombre, EstadoMedicion.ERROR, "Salida de medicion ilegible")

    resultado = ResultadoModelo(nombre, EstadoMedicion.OK, metricas=metricas)
    if referencia is not None:
        resultado.wer = round(wer(referencia, str(metricas.get("texto", ""))), 3)
    return resultado


def ejecutar_benchmark(
    modelos: Sequence[str],
    models_dir: Path,
    audio: Path,
    referencia: str | None,
    timeout_s: int,
    spacy_modelo: str | None = None,
    ejecutor: Ejecutor = ejecutor_subproceso,
    lector_entorno: Callable[[], EntornoContenedor] = leer_entorno,
) -> InformeBenchmark:
    resultados = [
        medir_modelo(m, models_dir, audio, referencia, timeout_s, spacy_modelo, ejecutor)
        for m in modelos
    ]
    return InformeBenchmark(entorno=lector_entorno(), audio=audio.name, resultados=resultados)
