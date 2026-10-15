"""actaflow.system.v1.ServiceStatusService implementado por el motor."""

from __future__ import annotations

import time

import grpc
from google.protobuf import timestamp_pb2

from actaflow.system.v1 import service_status_pb2 as pb
from actaflow.system.v1 import service_status_pb2_grpc
from actaflow_engine import __version__
from actaflow_engine.config import Settings
from actaflow_engine.inventario import inventario
from actaflow_engine.rpc import METADATO_TRANSPORTE, TRANSPORTE_GRPC_WEB

NOMBRE_SERVICIO = "ai-engine"


def transporte(contexto: grpc.aio.ServicerContext) -> pb.Transport.ValueType:
    metadatos = dict(contexto.invocation_metadata() or ())
    if metadatos.get(METADATO_TRANSPORTE) == TRANSPORTE_GRPC_WEB:
        return pb.TRANSPORT_GRPC_WEB
    return pb.TRANSPORT_GRPC


def construir_estado(settings: Settings, via: pb.Transport.ValueType) -> pb.ServiceStatus:
    inicio = time.perf_counter()
    inv = inventario(settings.models_dir, settings.asr_model)
    latencia = int((time.perf_counter() - inicio) * 1000)

    asr = pb.ComponentStatus(
        id="speech-model",
        kind=pb.COMPONENT_KIND_MODEL,
        latency_ms=latencia,
        version=f"faster-whisper-{inv.asr_configurado}-int8",
    )
    if inv.asr_listo:
        asr.state = pb.HEALTH_STATE_OK
        asr.detail = f"Modelo de voz {inv.asr_configurado} listo"
    else:
        asr.state = pb.HEALTH_STATE_DEGRADED
        asr.detail = f"Modelo de voz {inv.asr_configurado} no instalado"

    nlp = pb.ComponentStatus(id="nlp-model", kind=pb.COMPONENT_KIND_MODEL, latency_ms=latencia)
    if inv.nlp_disponibles:
        nlp.state = pb.HEALTH_STATE_OK
        nlp.version = inv.nlp_disponibles[0]
        nlp.detail = f"Modelo de lenguaje {inv.nlp_disponibles[0]} instalado"
    else:
        nlp.state = pb.HEALTH_STATE_DEGRADED
        nlp.detail = "Modelo de lenguaje de spaCy no instalado"

    componentes = [asr, nlp]
    todo_ok = all(c.state == pb.HEALTH_STATE_OK for c in componentes)
    marca = timestamp_pb2.Timestamp()
    marca.GetCurrentTime()
    return pb.ServiceStatus(
        service_name=NOMBRE_SERVICIO,
        version=__version__,
        state=pb.HEALTH_STATE_OK if todo_ok else pb.HEALTH_STATE_DEGRADED,
        checked_at=marca,
        served_via=via,
        components=componentes,
    )


class ServicioEstado(service_status_pb2_grpc.ServiceStatusServiceServicer):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def GetServiceStatus(  # noqa: N802 - nombre impuesto por el codigo generado
        self, request: pb.GetServiceStatusRequest, context: grpc.aio.ServicerContext
    ) -> pb.GetServiceStatusResponse:
        return pb.GetServiceStatusResponse(
            status=construir_estado(self._settings, transporte(context))
        )
