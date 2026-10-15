"""Interceptor del servidor gRPC: firma HMAC y reglas del contrato en cada llamada.

Para firmar exactamente lo que viajo por la red, el interceptor reemplaza el deserializador
del metodo: recibe los bytes protobuf crudos, verifica la firma sobre ellos, y solo entonces
deserializa, valida con protovalidate y llama al servicio.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import grpc
import protovalidate
from google.protobuf import any_pb2
from google.protobuf.message import DecodeError
from google.rpc import code_pb2, status_pb2

from actaflow.common.v1 import errors_pb2
from actaflow_engine.seguridad.hmac_firma import (
    METADATO_FIRMA,
    METADATO_TIMESTAMP,
    SIN_CUERPO,
    FirmaInvalidaError,
    VerificadorFirma,
)

log = logging.getLogger("actaflow_engine.rpc")

# La reflexion gRPC solo describe el contrato publico y nunca se expone fuera del contenedor.
EXENTOS = ("/grpc.reflection.",)


def _ruta_campo(violacion: Any) -> str:
    partes: list[str] = []
    for elemento in violacion.proto.field.elements:
        if elemento.HasField("index"):
            partes[-1] = f"{partes[-1]}[{elemento.index}]" if partes else f"[{elemento.index}]"
            continue
        partes.append(elemento.field_name)
        for clave in ("string_key", "int_key", "uint_key", "bool_key"):
            if elemento.HasField(clave):
                partes[-1] = f"{partes[-1]}[{getattr(elemento, clave)}]"
    return ".".join(partes)


def violaciones_del_contrato(mensaje: Any) -> errors_pb2.FieldViolations:
    """Reglas protovalidate que incumple el mensaje, en el formato de error del contrato."""
    resultado = errors_pb2.FieldViolations()
    for violacion in protovalidate.collect_violations(mensaje):
        resultado.violations.add(
            field=_ruta_campo(violacion),
            rule=violacion.proto.rule_id,
            description=violacion.proto.message,
        )
    return resultado


def metadatos_de_estado(codigo: int, mensaje: str, detalle: Any) -> tuple[tuple[str, bytes], ...]:
    """Trailer grpc-status-details-bin con un google.rpc.Status y el detalle tipado."""
    empaquetado = any_pb2.Any()
    empaquetado.Pack(detalle)
    estado = status_pb2.Status(code=codigo, message=mensaje, details=[empaquetado])
    return (("grpc-status-details-bin", estado.SerializeToString()),)


class InterceptorSeguridad(grpc.aio.ServerInterceptor):
    def __init__(self, verificador: VerificadorFirma, validar: bool = True) -> None:
        self._verificador = verificador
        self._validar = validar

    async def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Awaitable[grpc.RpcMethodHandler]],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        handler = await continuation(handler_call_details)
        metodo = handler_call_details.method
        if handler is None or metodo.startswith(EXENTOS):
            return handler
        metadatos = dict(handler_call_details.invocation_metadata or ())
        if handler.request_streaming:
            return self._envolver_flujo_entrante(handler, metodo, metadatos)
        return self._envolver_unario(handler, metodo, metadatos)

    def _rechazo_firma(self, metadatos: dict[str, str], metodo: str, cuerpo: bytes) -> str | None:
        try:
            self._verificador.verificar(
                metadatos.get(METADATO_TIMESTAMP), metadatos.get(METADATO_FIRMA), metodo, cuerpo
            )
        except FirmaInvalidaError as exc:
            log.warning("Llamada rechazada por firma: %s (%s)", metodo, exc.motivo.value)
            return exc.motivo.value
        return None

    async def _parsear(
        self, deserializar: Callable[[bytes], Any], crudo: bytes, contexto: grpc.aio.ServicerContext
    ) -> Any:
        try:
            peticion = deserializar(crudo)
        except DecodeError:
            await contexto.abort(grpc.StatusCode.INVALID_ARGUMENT, "Mensaje protobuf ilegible")
        if self._validar:
            violaciones = violaciones_del_contrato(peticion)
            if violaciones.violations:
                mensaje = "La peticion incumple el contrato"
                await contexto.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    mensaje,
                    trailing_metadata=metadatos_de_estado(
                        code_pb2.INVALID_ARGUMENT, mensaje, violaciones
                    ),
                )
        return peticion

    def _envolver_unario(
        self, handler: grpc.RpcMethodHandler, metodo: str, metadatos: dict[str, str]
    ) -> grpc.RpcMethodHandler:
        deserializar = handler.request_deserializer

        async def preparar(crudo: bytes, contexto: grpc.aio.ServicerContext) -> Any:
            if self._rechazo_firma(metadatos, metodo, crudo):
                await contexto.abort(grpc.StatusCode.UNAUTHENTICATED, "Llamada no autorizada")
            return await self._parsear(deserializar, crudo, contexto)

        if handler.unary_unary is not None:
            original = handler.unary_unary

            async def unario(crudo: bytes, contexto: grpc.aio.ServicerContext) -> Any:
                return await original(await preparar(crudo, contexto), contexto)

            return grpc.unary_unary_rpc_method_handler(
                unario, request_deserializer=None, response_serializer=handler.response_serializer
            )

        original_flujo = handler.unary_stream

        async def flujo(crudo: bytes, contexto: grpc.aio.ServicerContext) -> AsyncIterator[Any]:
            peticion = await preparar(crudo, contexto)
            resultado = original_flujo(peticion, contexto)
            if inspect.isasyncgen(resultado):
                async for respuesta in resultado:
                    yield respuesta
            else:
                await resultado

        return grpc.unary_stream_rpc_method_handler(
            flujo, request_deserializer=None, response_serializer=handler.response_serializer
        )

    def _envolver_flujo_entrante(
        self, handler: grpc.RpcMethodHandler, metodo: str, metadatos: dict[str, str]
    ) -> grpc.RpcMethodHandler:
        rechazo = self._rechazo_firma(metadatos, metodo, SIN_CUERPO)
        original = handler.stream_stream or handler.stream_unary

        async def validados(
            entrada: AsyncIterator[Any], contexto: grpc.aio.ServicerContext
        ) -> AsyncIterator[Any]:
            async for peticion in entrada:
                if self._validar and violaciones_del_contrato(peticion).violations:
                    await contexto.abort(
                        grpc.StatusCode.INVALID_ARGUMENT, "Un mensaje incumple el contrato"
                    )
                yield peticion

        async def comprobar(contexto: grpc.aio.ServicerContext) -> None:
            if rechazo:
                await contexto.abort(grpc.StatusCode.UNAUTHENTICATED, "Llamada no autorizada")

        if handler.stream_stream is not None:

            async def bidireccional(
                entrada: AsyncIterator[Any], contexto: grpc.aio.ServicerContext
            ) -> AsyncIterator[Any]:
                await comprobar(contexto)
                async for respuesta in original(validados(entrada, contexto), contexto):
                    yield respuesta

            return grpc.stream_stream_rpc_method_handler(
                bidireccional,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        async def entrante(entrada: AsyncIterator[Any], contexto: grpc.aio.ServicerContext) -> Any:
            await comprobar(contexto)
            return await original(validados(entrada, contexto), contexto)

        return grpc.stream_unary_rpc_method_handler(
            entrante,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
