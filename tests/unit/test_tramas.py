from __future__ import annotations

import base64

import pytest

from actaflow_engine.rpc import tramas


def test_una_trama_de_datos_tiene_bandera_cero_y_longitud_big_endian():
    assert tramas.trama_datos(b"\x0a\x01\x01") == b"\x00\x00\x00\x00\x03\x0a\x01\x01"


def test_un_mensaje_vacio_tambien_viaja_en_una_trama():
    assert tramas.trama_datos(b"") == b"\x00\x00\x00\x00\x00"


def test_decodificar_separa_datos_y_trailers():
    cuerpo = tramas.trama_datos(b"abc") + tramas.trama_trailers(0)
    resultado = tramas.decodificar(cuerpo, 100)
    assert [t.contenido for t in resultado if not t.es_trailers] == [b"abc"]
    assert tramas.leer_trailers(resultado[1].contenido) == {"grpc-status": "0"}


@pytest.mark.parametrize(
    ("cuerpo", "error"),
    [
        (b"\x00\x00\x00", "incompleta"),
        (b"\x00\x00\x00\x00\x09abc", "truncada"),
        (b"\x01\x00\x00\x00\x01a", "Compresion"),
        (b"\x02\x00\x00\x00\x01a", "Bandera desconocida"),
        (b"\x00\x00\x00\x10\x00" + b"x" * 4096, "supera el maximo"),
    ],
)
def test_rechaza_cuerpos_malformados(cuerpo, error):
    with pytest.raises(tramas.TramaInvalidaError, match=error):
        tramas.decodificar(cuerpo, 100)


def test_los_trailers_codifican_el_mensaje_en_porcentaje_y_se_leen_de_vuelta():
    trama = tramas.trama_trailers(16, "Llamada no autorizada: ñ y %")
    contenido = tramas.decodificar(trama, 1000)[0].contenido
    assert b"grpc-status:16\r\n" in contenido
    assert tramas.leer_trailers(contenido)["grpc-message"] == "Llamada no autorizada: ñ y %"


def test_los_metadatos_binarios_viajan_en_base64_sin_relleno():
    trama = tramas.trama_trailers(3, "x", [("grpc-status-details-bin", b"\x01\x02\xff")])
    leidos = tramas.leer_trailers(tramas.decodificar(trama, 1000)[0].contenido)
    valor = leidos["grpc-status-details-bin"]
    assert "=" not in valor
    assert base64.b64decode(valor + "=" * (-len(valor) % 4)) == b"\x01\x02\xff"


def test_no_se_duplican_grpc_status_ni_grpc_message_desde_los_metadatos():
    trama = tramas.trama_trailers(0, "", [("grpc-status", "13"), ("X-Extra", "1")])
    leidos = tramas.leer_trailers(tramas.decodificar(trama, 1000)[0].contenido)
    assert leidos == {"grpc-status": "0", "x-extra": "1"}
