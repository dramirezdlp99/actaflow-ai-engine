"""Pasarela gRPC-Web -> gRPC nativo, dentro del mismo contenedor.

Render Free solo expone HTTP/1.1 hacia internet, y gRPC nativo necesita HTTP/2. Esta pasarela
recibe gRPC-Web por el puerto web, desarma las tramas y reenvia la llamada al servidor gRPC
nativo del propio motor (127.0.0.1). Asi la firma, la validacion y los servicios son
exactamente los mismos por ambos transportes.
"""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator

import grpc
from google.protobuf import descriptor_pool
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

from actaflow_engine.rpc import METADATO_TRANSPORTE, TRANSPORTE_GRPC_WEB, tramas

log = logging.getLogger("actaflow_engine.pasarela")

TIPO_GRPC_WEB = "application/grpc-web+proto"
TIPOS_ACEPTADOS = ("application/grpc-web", "application/grpc-web+proto")
RUTA_VALIDA = re.compile(
    r"^/(actaflow\.[a-z0-9_]+(?:\.[a-z0-9_]+)*\.v[0-9]+\.[A-Za-z0-9]+)/([A-Za-z0-9]+)$"
)
TIEMPO_POR_DEFECTO_S = 600.0
UNIDADES_TIMEOUT = {"H": 3600.0, "M": 60.0, "S": 1.0, "m": 1e-3, "u": 1e-6, "n": 1e-9}


def plazo(cabecera: str | None) -> float:
    """Convierte la cabecera grpc-timeout ("30S", "500m") en segundos."""
    if not cabecera or len(cabecera) < 2 or not cabecera[:-1].isdigit():
        return TIEMPO_POR_DEFECTO_S
    unidad = UNIDADES_TIMEOUT.get(cabecera[-1])
    return (
        min(int(cabecera[:-1]) * unidad, TIEMPO_POR_DEFECTO_S) if unidad else TIEMPO_POR_DEFECTO_S
    )


def metadatos_reenviados(cabeceras: dict[str, str]) -> list[tuple[str, str]]:
    """Solo se reenvian la firma, la sesion y el marcador de transporte (que pone la pasarela)."""
    reenviados = [
        (clave, valor)
        for clave, valor in cabeceras.items()
        if (clave.startswith("x-actaflow-") and clave != METADATO_TRANSPORTE)
        or clave == "authorization"
    ]
    reenviados.append((METADATO_TRANSPORTE, TRANSPORTE_GRPC_WEB))
    return reenviados


def respuesta_error(codigo: grpc.StatusCode, mensaje: str) -> Response:
    return Response(
        content=tramas.trama_trailers(codigo.value[0], mensaje),
        media_type=TIPO_GRPC_WEB,
        headers={"grpc-status": str(codigo.value[0])},
    )


class PasarelaGrpcWeb:
    def __init__(self, destino: str, max_mensaje: int) -> None:
        self._destino = destino
        self._max_mensaje = max_mensaje
        self._canal: grpc.aio.Channel | None = None

    async def iniciar(self) -> None:
        self._canal = grpc.aio.insecure_channel(
            self._destino,
            options=[
                ("grpc.max_receive_message_length", self._max_mensaje),
                ("grpc.max_send_message_length", self._max_mensaje),
            ],
        )

    async def cerrar(self) -> None:
        if self._canal is not None:
            await self._canal.close()

    async def atender(self, request: Request) -> Response:
        tipo = request.headers.get("content-type", "").split(";")[0].strip().lower()
        if tipo not in TIPOS_ACEPTADOS:
            return Response(status_code=415, content=b"Se esperaba application/grpc-web+proto")

        coincidencia = RUTA_VALIDA.match(request.url.path)
        if coincidencia is None:
            return respuesta_error(grpc.StatusCode.UNIMPLEMENTED, "Metodo desconocido")
        servicio, metodo = coincidencia.groups()
        try:
            descriptor = descriptor_pool.Default().FindMethodByName(f"{servicio}.{metodo}")
        except KeyError:
            return respuesta_error(grpc.StatusCode.UNIMPLEMENTED, "Metodo desconocido")
        if descriptor.client_streaming:
            return respuesta_error(
                grpc.StatusCode.UNIMPLEMENTED, "Este metodo requiere gRPC nativo sobre HTTP/2"
            )

        try:
            tramas_entrada = tramas.decodificar(await request.body(), self._max_mensaje)
        except tramas.TramaInvalidaError as exc:
            return respuesta_error(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        datos = [t for t in tramas_entrada if not t.es_trailers]
        if len(datos) > 1:
            return respuesta_error(grpc.StatusCode.INVALID_ARGUMENT, "Se esperaba un solo mensaje")
        mensaje = datos[0].contenido if datos else b""

        if self._canal is None:
            return respuesta_error(grpc.StatusCode.UNAVAILABLE, "El servidor gRPC no esta listo")
        ruta = f"/{servicio}/{metodo}"
        metadatos = metadatos_reenviados(dict(request.headers))
        tiempo = plazo(request.headers.get("grpc-timeout"))

        if descriptor.server_streaming:
            llamada = self._canal.unary_stream(ruta)(mensaje, metadata=metadatos, timeout=tiempo)
            return StreamingResponse(self._flujo(llamada), media_type=TIPO_GRPC_WEB)

        llamada = self._canal.unary_unary(ruta)(mensaje, metadata=metadatos, timeout=tiempo)
        try:
            respuesta = await llamada
        except grpc.aio.AioRpcError as exc:
            return Response(content=self._trailers_error(exc), media_type=TIPO_GRPC_WEB)
        cuerpo = tramas.trama_datos(respuesta) + tramas.trama_trailers(
            grpc.StatusCode.OK.value[0], "", await llamada.trailing_metadata() or ()
        )
        return Response(content=cuerpo, media_type=TIPO_GRPC_WEB)

    async def _flujo(self, llamada: grpc.aio.UnaryStreamCall) -> AsyncIterator[bytes]:
        try:
            async for respuesta in llamada:
                yield tramas.trama_datos(respuesta)
        except grpc.aio.AioRpcError as exc:
            yield self._trailers_error(exc)
            return
        yield tramas.trama_trailers(
            grpc.StatusCode.OK.value[0], "", await llamada.trailing_metadata() or ()
        )

    @staticmethod
    def _trailers_error(exc: grpc.aio.AioRpcError) -> bytes:
        codigo = exc.code()
        if codigo in (grpc.StatusCode.INTERNAL, grpc.StatusCode.UNKNOWN):
            log.warning("Error interno reenviado por la pasarela: %s", exc.details())
        return tramas.trama_trailers(
            codigo.value[0], exc.details() or "", exc.trailing_metadata() or ()
        )
