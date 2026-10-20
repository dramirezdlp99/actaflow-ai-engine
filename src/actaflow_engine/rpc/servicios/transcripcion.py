"""actaflow.engine.v1.TranscriptionService: voz a texto sobre audio sellado para el motor."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

import grpc
import protovalidate

from actaflow.engine.v1 import engine_pb2 as pb
from actaflow.engine.v1 import engine_pb2_grpc
from actaflow.legal.v1 import transcript_pb2
from actaflow_engine.seguridad.procesador import (
    ClaveProcesador,
    SobreInvalidoError,
    aad,
    abrir,
    cifrar,
    descifrar,
)
from actaflow_engine.voz.transcriptor import (
    FRECUENCIA,
    AudioInvalidoError,
    ModeloNoDisponibleError,
    Transcripcion,
    Transcriptor,
    decodificar,
)

TIPO_SEGMENTO = "actaflow.engine.v1.SealedAudioSegment"
TIPO_RESULTADO = "actaflow.legal.v1.TranscriptionResult"
# Cada trozo del flujo en vivo: bytes de audio (la continuacion del mismo Ogg o WAV).
TIPO_TROZO = "actaflow.engine.v1.AudioChunk"
SEGUNDOS_ENTRE_PARCIALES = 3.0

log = logging.getLogger("actaflow_engine.transcripcion")


def resultado(
    transcripcion: Transcripcion, idioma: str, hablante: str
) -> transcript_pb2.TranscriptionResult:
    return transcript_pb2.TranscriptionResult(
        segments=[
            transcript_pb2.TranscriptSegment(
                speaker_participant_id=hablante,
                start_ms=t.inicio_ms,
                end_ms=t.fin_ms,
                text=t.texto,
                confidence=t.confianza,
            )
            for t in transcripcion.tramos
        ],
        language=idioma,
        model=transcripcion.modelo,
        audio_duration_ms=transcripcion.duracion_ms,
        real_time_factor=transcripcion.factor_tiempo_real,
    )


class ServicioTranscripcion(engine_pb2_grpc.TranscriptionServiceServicer):
    def __init__(self, procesador: ClaveProcesador, transcriptor: Transcriptor) -> None:
        self._procesador = procesador
        self._transcriptor = transcriptor

    async def _transcribir(
        self, contexto: grpc.aio.ServicerContext, datos: bytes, **pistas
    ) -> Transcripcion:  # noqa: ANN003
        try:
            return await asyncio.to_thread(self._transcriptor.transcribir, datos, **pistas)
        except AudioInvalidoError as error:
            await contexto.abort(grpc.StatusCode.INVALID_ARGUMENT, str(error))
        except ModeloNoDisponibleError as error:
            await contexto.abort(grpc.StatusCode.FAILED_PRECONDITION, str(error))
        raise AssertionError("inalcanzable")

    async def TranscribeSegment(  # noqa: N802 - nombre impuesto por el codigo generado
        self, request: pb.TranscribeSegmentRequest, context: grpc.aio.ServicerContext
    ) -> pb.TranscribeSegmentResponse:
        try:
            abierto = abrir(
                self._procesador,
                request.audio,
                TIPO_SEGMENTO,
                aad("audio-segment", request.case_id, request.segment_id),
            )
        except SobreInvalidoError as error:
            log.warning("Audio sellado rechazado: %s", error)
            await context.abort(
                grpc.StatusCode.UNAUTHENTICATED, "No se pudo abrir el audio sellado"
            )
        segmento = pb.SealedAudioSegment()
        try:
            segmento.ParseFromString(abierto.datos)
            protovalidate.validate(segmento)
        except Exception:  # noqa: BLE001 - cualquier fallo de forma es un argumento invalido
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, "El audio sellado no cumple el contrato"
            )
        transcripcion = await self._transcribir(
            context,
            segmento.audio,
            nombres=list(segmento.hints.names),
            vocabulario=list(segmento.hints.vocabulary),
        )
        mensaje = resultado(transcripcion, request.language, segmento.speaker_participant_id)
        return pb.TranscribeSegmentResponse(
            transcript=cifrar(
                abierto.clave,
                abierto.id_clave,
                mensaje.SerializeToString(),
                TIPO_RESULTADO,
                aad("transcript", request.case_id, request.segment_id),
            )
        )

    async def StreamTranscription(  # noqa: N802 - nombre impuesto por el codigo generado
        self,
        request_iterator: AsyncIterator[pb.StreamTranscriptionRequest],
        context: grpc.aio.ServicerContext,
    ) -> AsyncIterator[pb.StreamTranscriptionResponse]:
        """Transcripcion en vivo: devuelve un parcial cada ~3 s de audio nuevo y el final al cerrar.

        Como un segmento, una sesion dura a lo sumo 30 s; la sala abre otra para seguir.
        """
        inicio = None
        clave = b""
        audio = bytearray()
        ultimo_parcial = 0.0
        numero = 0
        async for mensaje in request_iterator:
            if inicio is None:
                if mensaje.WhichOneof("payload") != "start":
                    await context.abort(
                        grpc.StatusCode.INVALID_ARGUMENT, "El primer mensaje debe ser start"
                    )
                inicio = mensaje.start
                try:
                    clave = self._procesador.desenvolver(inicio.content_key)
                except SobreInvalidoError:
                    await context.abort(
                        grpc.StatusCode.UNAUTHENTICATED, "No se pudo abrir la clave de la sesion"
                    )
                continue
            if mensaje.WhichOneof("payload") != "chunk":
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT, "Solo el primer mensaje es start"
                )
            try:
                audio += descifrar(
                    clave,
                    mensaje.chunk,
                    TIPO_TROZO,
                    aad("audio-chunk", inicio.case_id, f"{inicio.session_id}/{numero}"),
                )
            except SobreInvalidoError:
                await context.abort(
                    grpc.StatusCode.UNAUTHENTICATED, "Un trozo de audio no se pudo abrir"
                )
            numero += 1
            try:
                segundos = len(decodificar(bytes(audio))) / FRECUENCIA
            except AudioInvalidoError as error:
                if "30 segundos" in str(error):
                    await context.abort(
                        grpc.StatusCode.INVALID_ARGUMENT, "La sesion supera 30 segundos"
                    )
                continue  # un trozo a medias: se espera al siguiente
            if segundos - ultimo_parcial >= SEGUNDOS_ENTRE_PARCIALES:
                ultimo_parcial = segundos
                yield self._respuesta(
                    await self._transcribir(context, bytes(audio)), inicio, clave, numero, False
                )
        if inicio is None or not audio:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "La sesion no envio audio")
        yield self._respuesta(
            await self._transcribir(context, bytes(audio)), inicio, clave, "final", True
        )

    @staticmethod
    def _respuesta(
        transcripcion: Transcripcion,
        inicio: pb.StreamTranscriptionStart,
        clave: bytes,
        parte: int | str,
        final: bool,
    ) -> pb.StreamTranscriptionResponse:
        mensaje = resultado(transcripcion, "es-CO", "")
        return pb.StreamTranscriptionResponse(
            partial=cifrar(
                clave,
                f"sesion:{inicio.session_id}",
                mensaje.SerializeToString(),
                TIPO_RESULTADO,
                aad("transcript-partial", inicio.case_id, f"{inicio.session_id}/{parte}"),
            ),
            final=final,
        )
