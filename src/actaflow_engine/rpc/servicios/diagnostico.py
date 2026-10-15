"""actaflow.engine.v1.EngineDiagnosticsService: mediciones del motor en su entorno real."""

from __future__ import annotations

import asyncio
from importlib import resources

import grpc

from actaflow.engine.v1 import engine_pb2 as pb
from actaflow.engine.v1 import engine_pb2_grpc
from actaflow_engine.config import Settings
from actaflow_engine.diagnostico.benchmark import (
    Ejecutor,
    EstadoMedicion,
    InformeBenchmark,
    ResultadoModelo,
    ejecutar_benchmark,
)
from actaflow_engine.inventario import nlp_disponibles

NOMBRES_MODELO = {
    pb.MODEL_SIZE_TINY: "tiny",
    pb.MODEL_SIZE_BASE: "base",
    pb.MODEL_SIZE_SMALL: "small",
}
MODELOS_POR_NOMBRE = {v: k for k, v in NOMBRES_MODELO.items()}
RESULTADOS = {
    EstadoMedicion.OK: pb.BENCHMARK_OUTCOME_OK,
    EstadoMedicion.OOM: pb.BENCHMARK_OUTCOME_OUT_OF_MEMORY,
    EstadoMedicion.TIMEOUT: pb.BENCHMARK_OUTCOME_TIMEOUT,
    EstadoMedicion.ERROR: pb.BENCHMARK_OUTCOME_ERROR,
    EstadoMedicion.NO_INSTALADO: pb.BENCHMARK_OUTCOME_NOT_INSTALLED,
}


def guion_referencia() -> str:
    return (
        resources.files("actaflow_engine.diagnostico")
        .joinpath("muestras/guion_es.txt")
        .read_text(encoding="utf-8")
    )


def _numero(metricas: dict[str, object], clave: str) -> float:
    valor = metricas.get(clave)
    return float(valor) if isinstance(valor, int | float) else 0.0


def a_mensaje(resultado: ResultadoModelo) -> pb.ModelBenchmark:
    m = resultado.metricas
    return pb.ModelBenchmark(
        model=MODELOS_POR_NOMBRE[resultado.modelo],
        outcome=RESULTADOS[resultado.estado],
        detail=resultado.detalle or "",
        load_seconds=_numero(m, "carga_s"),
        transcription_seconds=_numero(m, "transcripcion_s"),
        audio_seconds=_numero(m, "duracion_audio_s"),
        real_time_factor=_numero(m, "factor_tiempo_real"),
        peak_memory_bytes=int(_numero(m, "rss_pico_bytes")),
        word_error_rate=resultado.wer or 0.0,
        text=str(m.get("texto", "")),
    )


def a_respuesta(informe: InformeBenchmark) -> pb.RunBenchmarkResponse:
    entorno = informe.entorno
    return pb.RunBenchmarkResponse(
        limits=pb.ContainerLimits(
            memory_limit_bytes=entorno.memoria_limite_bytes or 0,
            cpu_quota_cores=entorno.cpu_cuota_nucleos or 0.0,
            visible_cpus=entorno.cpus_visibles,
        ),
        results=[a_mensaje(r) for r in informe.resultados],
    )


class ServicioDiagnostico(engine_pb2_grpc.EngineDiagnosticsServiceServicer):
    def __init__(self, settings: Settings, ejecutor: Ejecutor) -> None:
        self._settings = settings
        self._ejecutor = ejecutor
        self._candado = asyncio.Lock()

    async def RunBenchmark(  # noqa: N802 - nombre impuesto por el codigo generado
        self, request: pb.RunBenchmarkRequest, context: grpc.aio.ServicerContext
    ) -> pb.RunBenchmarkResponse:
        if not self._settings.benchmark_audio.is_file():
            await context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                f"No existe el audio de prueba {self._settings.benchmark_audio.name}",
            )
        spacy_modelo = None
        if request.include_nlp:
            instalados = nlp_disponibles()
            if not instalados:
                await context.abort(
                    grpc.StatusCode.FAILED_PRECONDITION, "No hay modelos de spaCy instalados"
                )
            spacy_modelo = instalados[0]
        if self._candado.locked():
            await context.abort(
                grpc.StatusCode.FAILED_PRECONDITION, "Ya hay un benchmark ejecutandose"
            )
        async with self._candado:
            informe = await asyncio.to_thread(
                ejecutar_benchmark,
                [NOMBRES_MODELO[m] for m in request.models],
                self._settings.models_dir,
                self._settings.benchmark_audio,
                guion_referencia(),
                self._settings.benchmark_timeout_seconds,
                spacy_modelo,
                self._ejecutor,
            )
        return a_respuesta(informe)
