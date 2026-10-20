"""TranscriptionService por gRPC nativo: audio sellado para el motor y resultado cifrado."""

from __future__ import annotations

import os
import uuid

import grpc
import pytest

from actaflow.crypto.v1 import crypto_pb2, crypto_pb2_grpc
from actaflow.engine.v1 import engine_pb2, engine_pb2_grpc
from actaflow.legal.v1 import transcript_pb2
from actaflow_engine.main import create_app
from actaflow_engine.seguridad.hmac_firma import metadatos_firmados
from actaflow_engine.seguridad.procesador import aad, cifrar, descifrar, envolver
from actaflow_engine.voz.transcriptor import Transcriptor
from tests.audio_prueba import ogg_opus, wav
from tests.conftest import SECRETO_PRUEBA, arrancar, crear_modelo_falso
from tests.unit.test_transcriptor import ReconocedorFalso

CLAVES = "/actaflow.crypto.v1.ProcessorKeyService/GetProcessorKeys"
SEGMENTO = "/actaflow.engine.v1.TranscriptionService/TranscribeSegment"
EN_VIVO = "/actaflow.engine.v1.TranscriptionService/StreamTranscription"
CASO = str(uuid.uuid4())
ANA = str(uuid.uuid4())
TIPO_RESULTADO = "actaflow.legal.v1.TranscriptionResult"


@pytest.fixture
def canal(settings, ejecutor_ok, models_dir):
    crear_modelo_falso(models_dir, "tiny")
    settings.max_body_bytes = 2_000_000
    transcriptor = Transcriptor(models_dir, "tiny", cargar=lambda _: ReconocedorFalso())
    for motor in arrancar(
        create_app(settings, ejecutor_benchmark=ejecutor_ok, transcriptor=transcriptor)
    ):
        with grpc.insecure_channel(motor.destino_grpc) as canal:
            yield canal


def firmado(metodo, peticion=None):
    cuerpo = peticion.SerializeToString() if peticion is not None else b""
    return metadatos_firmados(SECRETO_PRUEBA, metodo, cuerpo)


def clave_del_motor(canal) -> crypto_pb2.PublicKey:
    peticion = crypto_pb2.GetProcessorKeysRequest()
    stub = crypto_pb2_grpc.ProcessorKeyServiceStub(canal)
    return stub.GetProcessorKeys(peticion, metadata=firmado(CLAVES, peticion)).keys[0].key


def segmento_sellado(
    canal, audio: bytes, segmento: str, codificacion=engine_pb2.AUDIO_ENCODING_WAV_PCM16
):
    publica = clave_del_motor(canal)
    clave = os.urandom(32)
    contenido = engine_pb2.SealedAudioSegment(
        audio=audio,
        encoding=codificacion,
        speaker_participant_id=ANA,
        hints=engine_pb2.RecognitionHints(names=["Ana Ruiz"], vocabulary=["convocante"]),
    )
    sobre = crypto_pb2.SealedEnvelope(
        payload=cifrar(
            clave,
            "audio:1",
            contenido.SerializeToString(),
            "actaflow.engine.v1.SealedAudioSegment",
            aad("audio-segment", CASO, segmento),
        ),
        processor_key=envolver(clave, publica.key_id, publica.public_key),
        content_key_for_case=cifrar(os.urandom(32), "caso:v1", clave, "clave", b"x"),
    )
    return clave, engine_pb2.TranscribeSegmentRequest(
        case_id=CASO, segment_id=segmento, audio=sobre, language="es-CO"
    )


@pytest.mark.parametrize(
    ("audio", "codificacion"),
    [
        (wav(2.0), engine_pb2.AUDIO_ENCODING_WAV_PCM16),
        (ogg_opus(2.0), engine_pb2.AUDIO_ENCODING_OGG_OPUS),
    ],
    ids=["wav", "ogg-opus"],
)
def test_transcribe_un_segmento_sellado(canal, audio, codificacion):
    segmento = str(uuid.uuid4())
    clave, peticion = segmento_sellado(canal, audio, segmento, codificacion)
    respuesta = engine_pb2_grpc.TranscriptionServiceStub(canal).TranscribeSegment(
        peticion, metadata=firmado(SEGMENTO, peticion)
    )
    resultado = transcript_pb2.TranscriptionResult.FromString(
        descifrar(clave, respuesta.transcript, TIPO_RESULTADO, aad("transcript", CASO, segmento))
    )
    assert [s.text for s in resultado.segments] == ["Buenos días.", "Inicia la audiencia."]
    assert {s.speaker_participant_id for s in resultado.segments} == {ANA}
    assert (resultado.language, resultado.model) == ("es-CO", "faster-whisper-tiny-int8")
    assert abs(resultado.audio_duration_ms - 2000) <= 10


def test_audio_ilegible_o_sobre_ajeno(canal):
    stub = engine_pb2_grpc.TranscriptionServiceStub(canal)
    _, peticion = segmento_sellado(canal, b"no es audio", str(uuid.uuid4()))
    with pytest.raises(grpc.RpcError) as error:
        stub.TranscribeSegment(peticion, metadata=firmado(SEGMENTO, peticion))
    assert error.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    _, peticion = segmento_sellado(canal, wav(1.0), str(uuid.uuid4()))
    peticion.segment_id = str(uuid.uuid4())  # el AAD ya no coincide
    with pytest.raises(grpc.RpcError) as error:
        stub.TranscribeSegment(peticion, metadata=firmado(SEGMENTO, peticion))
    assert error.value.code() == grpc.StatusCode.UNAUTHENTICATED


def test_transcripcion_en_vivo_con_parciales_y_final(canal):
    publica = clave_del_motor(canal)
    clave = os.urandom(32)
    sesion = str(uuid.uuid4())
    audio = wav(7.0)
    trozos = [audio[i : i + 40_000] for i in range(0, len(audio), 40_000)]

    def mensajes():
        yield engine_pb2.StreamTranscriptionRequest(
            start=engine_pb2.StreamTranscriptionStart(
                case_id=CASO,
                session_id=sesion,
                encoding=engine_pb2.AUDIO_ENCODING_WAV_PCM16,
                content_key=envolver(clave, publica.key_id, publica.public_key),
            )
        )
        for n, trozo in enumerate(trozos):
            yield engine_pb2.StreamTranscriptionRequest(
                chunk=cifrar(
                    clave,
                    "sesion",
                    trozo,
                    "actaflow.engine.v1.AudioChunk",
                    aad("audio-chunk", CASO, f"{sesion}/{n}"),
                )
            )

    respuestas = list(
        engine_pb2_grpc.TranscriptionServiceStub(canal).StreamTranscription(
            mensajes(), metadata=firmado(EN_VIVO)
        )
    )
    assert [r.final for r in respuestas] == [False, False, True]
    final = transcript_pb2.TranscriptionResult.FromString(
        descifrar(
            clave,
            respuestas[-1].partial,
            TIPO_RESULTADO,
            aad("transcript-partial", CASO, f"{sesion}/final"),
        )
    )
    assert final.segments[0].text == "Buenos días." and abs(final.audio_duration_ms - 7000) <= 10


def test_en_vivo_exige_start_primero(canal):
    def mensajes():
        yield engine_pb2.StreamTranscriptionRequest(
            chunk=crypto_pb2.EncryptedBlob(
                suite=crypto_pb2.CIPHER_SUITE_AES_256_GCM,
                key_id="x",
                nonce=bytes(12),
                ciphertext=bytes(16),
            )
        )

    with pytest.raises(grpc.RpcError) as error:
        list(
            engine_pb2_grpc.TranscriptionServiceStub(canal).StreamTranscription(
                mensajes(), metadata=firmado(EN_VIVO)
            )
        )
    assert error.value.code() == grpc.StatusCode.INVALID_ARGUMENT
