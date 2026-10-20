"""ExtractionService de punta a punta por gRPC nativo: sellado para el motor, resultado cifrado."""

from __future__ import annotations

import os
import uuid

import grpc
import pytest

from actaflow.common.v1 import values_pb2
from actaflow.crypto.v1 import crypto_pb2, crypto_pb2_grpc
from actaflow.engine.v1 import engine_pb2, engine_pb2_grpc
from actaflow.legal.v1 import entities_pb2
from actaflow_engine.seguridad.hmac_firma import metadatos_firmados
from actaflow_engine.seguridad.procesador import aad, cifrar, descifrar, envolver
from tests.conftest import SECRETO_PRUEBA

CLAVES = "/actaflow.crypto.v1.ProcessorKeyService/GetProcessorKeys"
EXTRAER = "/actaflow.engine.v1.ExtractionService/ExtractEntities"
CASO = str(uuid.uuid4())


@pytest.fixture
def canal(motor):
    with grpc.insecure_channel(motor.destino_grpc) as canal:
        yield canal


def firmado(metodo, peticion):
    return metadatos_firmados(SECRETO_PRUEBA, metodo, peticion.SerializeToString())


def clave_del_motor(canal) -> crypto_pb2.PublicKey:
    peticion = crypto_pb2.GetProcessorKeysRequest()
    (clave,) = (
        crypto_pb2_grpc.ProcessorKeyServiceStub(canal)
        .GetProcessorKeys(peticion, metadata=firmado(CLAVES, peticion))
        .keys
    )
    assert clave.kind == crypto_pb2.PROCESSOR_KIND_AI_ENGINE
    return clave.key


def peticion_sellada(
    canal, entrada: engine_pb2.ExtractionInput, extraccion: str, tipo=None, caso=CASO
):
    publica = clave_del_motor(canal)
    clave = os.urandom(32)
    sobre = crypto_pb2.SealedEnvelope(
        payload=cifrar(
            clave,
            "contenido:1",
            entrada.SerializeToString(),
            tipo or "actaflow.engine.v1.ExtractionInput",
            aad("extraction-input", caso, extraccion),
        ),
        processor_key=envolver(clave, publica.key_id, publica.public_key),
        content_key_for_case=cifrar(os.urandom(32), "caso:v1", clave, "clave-de-contenido", b"x"),
    )
    return clave, engine_pb2.ExtractEntitiesRequest(
        case_id=CASO, extraction_id=extraccion, input=sobre
    )


def test_la_clave_del_motor_es_un_punto_p256(canal):
    clave = clave_del_motor(canal)
    assert clave.algorithm == "ECDH-P256"
    assert len(clave.public_key) == 65 and clave.key_id.startswith("motor:")
    assert len(clave.fingerprint_sha256) == 64


def test_extrae_entidades_de_una_transcripcion_sellada(canal):
    extraccion = str(uuid.uuid4())
    entrada = engine_pb2.ExtractionInput(
        text="El convocado pagará $2.000.000 dentro de los 10 días hábiles siguientes.",
        reference_date=values_pb2.CalendarDate(year=2026, month=10, day=20),
    )
    clave, peticion = peticion_sellada(canal, entrada, extraccion)
    respuesta = engine_pb2_grpc.ExtractionServiceStub(canal).ExtractEntities(
        peticion, metadata=firmado(EXTRAER, peticion)
    )
    assert respuesta.entities.key_id == "contenido:1"
    resultado = entities_pb2.EntityExtractionResult()
    resultado.ParseFromString(
        descifrar(
            clave,
            respuesta.entities,
            "actaflow.legal.v1.EntityExtractionResult",
            aad("extraction-result", CASO, extraccion),
        )
    )
    assert resultado.amounts[0].amount.amount.units == 2_000_000
    assert resultado.deadlines[0].deadline.days == 10
    # El resultado no se abre en otro contexto (otro recurso).
    with pytest.raises(Exception, match="descifrar"):
        descifrar(
            clave,
            respuesta.entities,
            "actaflow.legal.v1.EntityExtractionResult",
            aad("extraction-result", CASO, str(uuid.uuid4())),
        )


def test_rechaza_un_sobre_de_otro_contexto_o_con_entrada_invalida(canal):
    stub = engine_pb2_grpc.ExtractionServiceStub(canal)
    entrada = engine_pb2.ExtractionInput(
        text="Hola", reference_date=values_pb2.CalendarDate(year=2026, month=10, day=20)
    )
    _, peticion = peticion_sellada(canal, entrada, str(uuid.uuid4()), caso=str(uuid.uuid4()))
    with pytest.raises(grpc.RpcError) as error:
        stub.ExtractEntities(peticion, metadata=firmado(EXTRAER, peticion))
    assert error.value.code() == grpc.StatusCode.UNAUTHENTICATED

    _, peticion = peticion_sellada(canal, entrada, str(uuid.uuid4()), tipo="otro.Tipo")
    with pytest.raises(grpc.RpcError) as error:
        stub.ExtractEntities(peticion, metadata=firmado(EXTRAER, peticion))
    assert error.value.code() == grpc.StatusCode.UNAUTHENTICATED

    sin_texto = engine_pb2.ExtractionInput(
        reference_date=values_pb2.CalendarDate(year=2026, month=10, day=20)
    )
    _, peticion = peticion_sellada(canal, sin_texto, str(uuid.uuid4()))
    with pytest.raises(grpc.RpcError) as error:
        stub.ExtractEntities(peticion, metadata=firmado(EXTRAER, peticion))
    assert error.value.code() == grpc.StatusCode.INVALID_ARGUMENT
