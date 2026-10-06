"""POST /v1/diagnostico/benchmark: mide memoria y velocidad de cada modelo en el
entorno real. Exige firma HMAC y solo admite un benchmark a la vez."""

from __future__ import annotations

import threading
from importlib import resources
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator

from actaflow_engine.config import Settings
from actaflow_engine.diagnostico.benchmark import Ejecutor, ejecutar_benchmark
from actaflow_engine.errores import MotorError
from actaflow_engine.inventario import nlp_disponibles
from actaflow_engine.seguridad.dependencias import exigir_firma

router = APIRouter(prefix="/v1/diagnostico", tags=["diagnostico"])

_candado = threading.Lock()

NombreModelo = Literal["tiny", "base", "small"]


class SolicitudBenchmark(BaseModel):
    modelos: Annotated[list[NombreModelo], Field(min_length=1, max_length=3)]
    con_spacy: bool = False

    @field_validator("modelos")
    @classmethod
    def _sin_repetidos(cls, valor: list[str]) -> list[str]:
        if len(set(valor)) != len(valor):
            raise ValueError("modelos repetidos")
        return valor


def guion_referencia() -> str:
    return (
        resources.files("actaflow_engine.diagnostico")
        .joinpath("muestras/guion_es.txt")
        .read_text(encoding="utf-8")
    )


@router.post("/benchmark", dependencies=[Depends(exigir_firma)])
async def benchmark(solicitud: SolicitudBenchmark, request: Request) -> dict[str, object]:
    settings: Settings = request.app.state.settings
    ejecutor: Ejecutor = request.app.state.ejecutor_benchmark

    if not settings.benchmark_audio.is_file():
        raise MotorError(
            409,
            "audio_no_disponible",
            f"No existe el audio de prueba {settings.benchmark_audio.name}",
        )
    spacy_modelo = None
    if solicitud.con_spacy:
        instalados = nlp_disponibles()
        if not instalados:
            raise MotorError(409, "spacy_no_disponible", "No hay modelos de spaCy instalados")
        spacy_modelo = instalados[0]

    if not _candado.acquire(blocking=False):
        raise MotorError(409, "benchmark_en_curso", "Ya hay un benchmark ejecutandose")
    try:
        informe = await run_in_threadpool(
            ejecutar_benchmark,
            solicitud.modelos,
            settings.models_dir,
            settings.benchmark_audio,
            guion_referencia(),
            settings.benchmark_timeout_seconds,
            spacy_modelo,
            ejecutor,
        )
    finally:
        _candado.release()
    return informe.como_dict()
