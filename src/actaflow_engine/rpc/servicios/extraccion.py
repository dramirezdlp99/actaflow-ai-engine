"""actaflow.engine.v1.ExtractionService y actaflow.crypto.v1.ProcessorKeyService."""

from __future__ import annotations

import asyncio
import logging
from datetime import date

import grpc
import protovalidate

from actaflow.crypto.v1 import crypto_pb2, crypto_pb2_grpc
from actaflow.engine.v1 import engine_pb2 as pb
from actaflow.engine.v1 import engine_pb2_grpc
from actaflow_engine.extraccion.extractor import extraer
from actaflow_engine.seguridad.procesador import (
    ClaveProcesador,
    SobreInvalidoError,
    aad,
    abrir,
    cifrar,
)

TIPO_ENTRADA = "actaflow.engine.v1.ExtractionInput"
TIPO_RESULTADO = "actaflow.legal.v1.EntityExtractionResult"

log = logging.getLogger("actaflow_engine.extraccion")


class ServicioClaves(crypto_pb2_grpc.ProcessorKeyServiceServicer):
    """Clave publica del motor, para que el navegador le selle contenido."""

    def __init__(self, procesador: ClaveProcesador) -> None:
        self._procesador = procesador

    async def GetProcessorKeys(  # noqa: N802 - nombre impuesto por el codigo generado
        self, request: crypto_pb2.GetProcessorKeysRequest, context: grpc.aio.ServicerContext
    ) -> crypto_pb2.GetProcessorKeysResponse:
        return crypto_pb2.GetProcessorKeysResponse(
            keys=[
                crypto_pb2.ProcessorKey(
                    kind=crypto_pb2.PROCESSOR_KIND_AI_ENGINE, key=self._procesador.clave_publica()
                )
            ]
        )


class ServicioExtraccion(engine_pb2_grpc.ExtractionServiceServicer):
    """Abre la transcripcion sellada en memoria, extrae las entidades y las devuelve cifradas."""

    def __init__(self, procesador: ClaveProcesador) -> None:
        self._procesador = procesador

    async def ExtractEntities(  # noqa: N802 - nombre impuesto por el codigo generado
        self, request: pb.ExtractEntitiesRequest, context: grpc.aio.ServicerContext
    ) -> pb.ExtractEntitiesResponse:
        try:
            abierto = abrir(
                self._procesador,
                request.input,
                TIPO_ENTRADA,
                aad("extraction-input", request.case_id, request.extraction_id),
            )
        except SobreInvalidoError as error:
            log.warning("Sobre de extraccion rechazado: %s", error)
            await context.abort(
                grpc.StatusCode.UNAUTHENTICATED, "No se pudo abrir el contenido sellado"
            )
        entrada = pb.ExtractionInput()
        try:
            entrada.ParseFromString(abierto.datos)
            protovalidate.validate(entrada)
        except Exception:  # noqa: BLE001 - cualquier fallo de forma es un argumento invalido
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, "La entrada sellada no cumple el contrato"
            )
        referencia = entrada.reference_date
        try:
            dia = date(referencia.year, referencia.month, referencia.day)
        except ValueError:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, "reference_date no es una fecha valida"
            )
        participantes = [(p.participant_id, p.display_name) for p in entrada.participants]
        resultado = await asyncio.to_thread(extraer, entrada.text, dia, participantes)
        return pb.ExtractEntitiesResponse(
            entities=cifrar(
                abierto.clave,
                abierto.id_clave,
                resultado.SerializeToString(),
                TIPO_RESULTADO,
                aad("extraction-result", request.case_id, request.extraction_id),
            )
        )
