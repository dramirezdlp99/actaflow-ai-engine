"""DocumentService: el motor hace de procesador de documentos para el acta final.

Abre en memoria el contenido final que el navegador sello para el, genera el PDF y lo devuelve
cifrado con la misma clave de contenido, junto con su SHA-256: legal-case sella ese hash sin ver
el documento.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging

import grpc
import protovalidate

from actaflow.engine.v1 import engine_pb2 as pb
from actaflow.engine.v1 import engine_pb2_grpc
from actaflow.minutes.v1 import minute_pb2
from actaflow_engine.documentos.pdf import DocumentoDemasiadoLargoError, renderizar
from actaflow_engine.seguridad.procesador import (
    ClaveProcesador,
    SobreInvalidoError,
    aad,
    abrir,
    cifrar,
)

log = logging.getLogger("actaflow_engine.documentos")
TIPO_ENTRADA = "actaflow.minutes.v1.FinalContent"
TIPO_PDF = "application/pdf"


class ServicioDocumentos(engine_pb2_grpc.DocumentServiceServicer):
    def __init__(self, procesador: ClaveProcesador) -> None:
        self._procesador = procesador

    async def RenderMinutePdf(  # noqa: N802 - nombre impuesto por el codigo generado
        self, request: pb.RenderMinutePdfRequest, context: grpc.aio.ServicerContext
    ) -> pb.RenderMinutePdfResponse:
        try:
            abierto = abrir(
                self._procesador,
                request.final_content,
                TIPO_ENTRADA,
                aad("minute-final", request.case_id, request.minute_id),
            )
        except SobreInvalidoError as error:
            log.warning("Sobre del acta rechazado: %s", error)
            await context.abort(
                grpc.StatusCode.UNAUTHENTICATED, "No se pudo abrir el contenido sellado"
            )
        contenido = minute_pb2.FinalContent()
        try:
            contenido.ParseFromString(abierto.datos)
            protovalidate.validate(contenido)
        except Exception:  # noqa: BLE001 - cualquier fallo de forma es un argumento invalido
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, "El contenido sellado no cumple el contrato"
            )
        try:
            pdf, paginas = await asyncio.to_thread(renderizar, contenido.title, contenido.html)
        except DocumentoDemasiadoLargoError as error:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(error))
        return pb.RenderMinutePdfResponse(
            pdf=cifrar(
                abierto.clave,
                abierto.id_clave,
                pdf,
                TIPO_PDF,
                aad("minute-pdf", request.case_id, request.minute_id),
            ),
            sha256_hex=hashlib.sha256(pdf).hexdigest(),
            page_count=paginas,
        )
