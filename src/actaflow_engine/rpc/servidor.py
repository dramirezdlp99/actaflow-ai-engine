"""Servidor gRPC nativo (HTTP/2) del motor."""

from __future__ import annotations

import grpc
from grpc_reflection.v1alpha import reflection

from actaflow.crypto.v1 import crypto_pb2, crypto_pb2_grpc
from actaflow.engine.v1 import engine_pb2, engine_pb2_grpc
from actaflow.system.v1 import service_status_pb2, service_status_pb2_grpc
from actaflow_engine.config import Settings
from actaflow_engine.diagnostico.benchmark import Ejecutor
from actaflow_engine.rpc.interceptor import InterceptorSeguridad
from actaflow_engine.rpc.servicios.diagnostico import ServicioDiagnostico
from actaflow_engine.rpc.servicios.documentos import ServicioDocumentos
from actaflow_engine.rpc.servicios.estado import ServicioEstado
from actaflow_engine.rpc.servicios.extraccion import ServicioClaves, ServicioExtraccion
from actaflow_engine.rpc.servicios.transcripcion import ServicioTranscripcion
from actaflow_engine.seguridad.hmac_firma import VerificadorFirma
from actaflow_engine.seguridad.procesador import ClaveProcesador, clave_desde_entorno
from actaflow_engine.voz.transcriptor import Transcriptor

SERVICIOS_PUBLICADOS = (
    service_status_pb2.DESCRIPTOR.services_by_name["ServiceStatusService"].full_name,
    engine_pb2.DESCRIPTOR.services_by_name["EngineDiagnosticsService"].full_name,
    engine_pb2.DESCRIPTOR.services_by_name["ExtractionService"].full_name,
    engine_pb2.DESCRIPTOR.services_by_name["TranscriptionService"].full_name,
    engine_pb2.DESCRIPTOR.services_by_name["DocumentService"].full_name,
    crypto_pb2.DESCRIPTOR.services_by_name["ProcessorKeyService"].full_name,
)


def crear_servidor(
    settings: Settings,
    ejecutor: Ejecutor,
    procesador: ClaveProcesador | None = None,
    transcriptor: Transcriptor | None = None,
) -> tuple[grpc.aio.Server, int]:
    """Crea (sin iniciar) el servidor y devuelve el puerto asignado."""
    if procesador is None:
        secreto = settings.processor_private_key
        procesador = clave_desde_entorno(
            secreto.get_secret_value() if secreto else None, settings.es_produccion
        )
    verificador = VerificadorFirma(
        secreto=settings.hmac_secret.get_secret_value(),
        tolerancia_segundos=settings.hmac_tolerance_seconds,
    )
    servidor = grpc.aio.server(
        interceptors=[InterceptorSeguridad(verificador)],
        options=[
            ("grpc.max_receive_message_length", settings.max_body_bytes),
            ("grpc.max_send_message_length", settings.max_body_bytes),
        ],
    )
    service_status_pb2_grpc.add_ServiceStatusServiceServicer_to_server(
        ServicioEstado(settings), servidor
    )
    engine_pb2_grpc.add_EngineDiagnosticsServiceServicer_to_server(
        ServicioDiagnostico(settings, ejecutor), servidor
    )
    engine_pb2_grpc.add_ExtractionServiceServicer_to_server(
        ServicioExtraccion(procesador), servidor
    )
    engine_pb2_grpc.add_TranscriptionServiceServicer_to_server(
        ServicioTranscripcion(
            procesador, transcriptor or Transcriptor(settings.models_dir, settings.asr_model)
        ),
        servidor,
    )
    engine_pb2_grpc.add_DocumentServiceServicer_to_server(ServicioDocumentos(procesador), servidor)
    crypto_pb2_grpc.add_ProcessorKeyServiceServicer_to_server(ServicioClaves(procesador), servidor)
    reflection.enable_server_reflection((*SERVICIOS_PUBLICADOS, reflection.SERVICE_NAME), servidor)
    puerto = servidor.add_insecure_port(settings.grpc_bind)
    if puerto == 0:
        raise RuntimeError(f"No se pudo abrir el puerto gRPC {settings.grpc_bind}")
    return servidor, puerto
