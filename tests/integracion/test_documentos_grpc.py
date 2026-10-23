"""DocumentService por gRPC nativo: el acta llega sellada y el PDF vuelve cifrado con su hash."""

from __future__ import annotations

import hashlib
import os
import uuid

import grpc
import pytest

from actaflow.crypto.v1 import crypto_pb2
from actaflow.engine.v1 import engine_pb2, engine_pb2_grpc
from actaflow.minutes.v1 import minute_pb2
from actaflow_engine.seguridad.procesador import aad, cifrar, descifrar, envolver
from tests.integracion.test_extraccion_grpc import clave_del_motor, firmado

RENDER = "/actaflow.engine.v1.DocumentService/RenderMinutePdf"
CASO = str(uuid.uuid4())


@pytest.fixture
def canal(motor):
    with grpc.insecure_channel(motor.destino_grpc) as canal:
        yield canal


def peticion(canal, contenido: minute_pb2.FinalContent, acta: str, proposito="minute-final"):
    publica = clave_del_motor(canal)
    clave = os.urandom(32)
    sobre = crypto_pb2.SealedEnvelope(
        payload=cifrar(
            clave,
            "contenido:acta",
            contenido.SerializeToString(),
            "actaflow.minutes.v1.FinalContent",
            aad(proposito, CASO, acta),
        ),
        processor_key=envolver(clave, publica.key_id, publica.public_key),
        content_key_for_case=cifrar(os.urandom(32), "caso:v1", clave, "clave-de-contenido", b"x"),
    )
    return clave, engine_pb2.RenderMinutePdfRequest(
        case_id=CASO, minute_id=acta, final_content=sobre
    )


def test_genera_el_pdf_del_acta_sellada_y_devuelve_su_hash(canal):
    acta = str(uuid.uuid4())
    contenido = minute_pb2.FinalContent(
        title="Acta de conciliación CC-2026-0400",
        html="<h2>ACTA DE CONCILIACIÓN</h2><p>El convocado pagará <strong>$ 1.500.000</strong></p>",
    )
    clave, pedido = peticion(canal, contenido, acta)
    respuesta = engine_pb2_grpc.DocumentServiceStub(canal).RenderMinutePdf(
        pedido, metadata=firmado(RENDER, pedido)
    )
    pdf = descifrar(clave, respuesta.pdf, "application/pdf", aad("minute-pdf", CASO, acta))
    assert pdf.startswith(b"%PDF-")
    assert respuesta.sha256_hex == hashlib.sha256(pdf).hexdigest()
    assert respuesta.page_count == 1
    assert respuesta.pdf.key_id == "contenido:acta"


def test_rechaza_un_sobre_de_otro_proposito_y_un_contenido_vacio(canal):
    stub = engine_pb2_grpc.DocumentServiceStub(canal)
    contenido = minute_pb2.FinalContent(title="Acta", html="<p>x</p>")
    _, ajeno = peticion(canal, contenido, str(uuid.uuid4()), proposito="extraction-input")
    with pytest.raises(grpc.RpcError) as error:
        stub.RenderMinutePdf(ajeno, metadata=firmado(RENDER, ajeno))
    assert error.value.code() == grpc.StatusCode.UNAUTHENTICATED

    _, vacio = peticion(canal, minute_pb2.FinalContent(title="Acta", html=""), str(uuid.uuid4()))
    with pytest.raises(grpc.RpcError) as error:
        stub.RenderMinutePdf(vacio, metadata=firmado(RENDER, vacio))
    assert error.value.code() == grpc.StatusCode.INVALID_ARGUMENT


def test_exige_la_firma_de_legal_case(canal):
    _, pedido = peticion(
        canal, minute_pb2.FinalContent(title="Acta", html="<p>x</p>"), str(uuid.uuid4())
    )
    with pytest.raises(grpc.RpcError) as error:
        engine_pb2_grpc.DocumentServiceStub(canal).RenderMinutePdf(pedido)
    assert error.value.code() == grpc.StatusCode.UNAUTHENTICATED
