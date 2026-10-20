"""Sellado para el motor: el mismo esquema de envoltura que el navegador (FE-4)."""

from __future__ import annotations

import os

import pytest

from actaflow.crypto.v1 import crypto_pb2
from actaflow_engine.config import Settings
from actaflow_engine.seguridad.procesador import (
    ClaveProcesador,
    SobreInvalidoError,
    aad,
    abrir,
    cifrar,
    clave_desde_entorno,
    descifrar,
    envolver,
)
from tests.conftest import SECRETO_PRUEBA


def sobre(procesador: ClaveProcesador, datos: bytes, contexto: bytes, clave: bytes | None = None):
    clave = clave or os.urandom(32)
    return clave, crypto_pb2.SealedEnvelope(
        payload=cifrar(clave, "contenido:1", datos, "x.Tipo", contexto),
        processor_key=envolver(clave, procesador.id_clave, procesador.publica),
        content_key_for_case=cifrar(os.urandom(32), "caso:1", clave, "k", b"k"),
    )


def test_abre_lo_sellado_y_el_resultado_usa_la_misma_clave():
    motor = ClaveProcesador.nueva()
    contexto = aad("extraction-input", "caso", "recurso")
    clave, sellado = sobre(motor, b"hola", contexto)
    abierto = abrir(motor, sellado, "x.Tipo", contexto)
    assert (abierto.datos, abierto.clave, abierto.id_clave) == (b"hola", clave, "contenido:1")
    assert len(motor.publica) == 65 and motor.publica[0] == 4
    assert motor.id_clave == f"motor:{motor.huella[:16]}"


def test_rechaza_otra_clave_otro_contexto_otro_tipo_o_datos_alterados():
    motor = ClaveProcesador.nueva()
    contexto = aad("extraction-input", "caso", "recurso")
    _, sellado = sobre(motor, b"hola", contexto)
    with pytest.raises(SobreInvalidoError):
        abrir(ClaveProcesador.nueva(), sellado, "x.Tipo", contexto)
    with pytest.raises(SobreInvalidoError):
        abrir(motor, sellado, "x.Tipo", aad("extraction-input", "otro-caso", "recurso"))
    with pytest.raises(SobreInvalidoError):
        abrir(motor, sellado, "otro.Tipo", contexto)
    alterado = crypto_pb2.SealedEnvelope()
    alterado.CopyFrom(sellado)
    alterado.processor_key.wrapped_key = bytes(48)
    with pytest.raises(SobreInvalidoError):
        abrir(motor, alterado, "x.Tipo", contexto)
    with pytest.raises(SobreInvalidoError):
        descifrar(os.urandom(32), sellado.payload, "x.Tipo", contexto)


def test_la_clave_va_y_vuelve_por_variable_de_entorno():
    motor = ClaveProcesador.nueva()
    otra = ClaveProcesador.desde_pkcs8(motor.pkcs8_base64url())
    assert otra.publica == motor.publica
    assert clave_desde_entorno(None, produccion=False).publica != motor.publica
    with pytest.raises(RuntimeError):
        clave_desde_entorno(None, produccion=True)


def test_produccion_exige_la_clave_del_procesador():
    with pytest.raises(ValueError, match="PROCESSOR_PRIVATE_KEY"):
        Settings(hmac_secret=SECRETO_PRUEBA, environment="produccion", _env_file=None)
    Settings(
        hmac_secret=SECRETO_PRUEBA,
        environment="produccion",
        processor_private_key=ClaveProcesador.nueva().pkcs8_base64url(),
        _env_file=None,
    )
