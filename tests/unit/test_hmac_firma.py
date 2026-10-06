from __future__ import annotations

import pytest

from actaflow_engine.seguridad.hmac_firma import (
    CABECERA_FIRMA,
    CABECERA_TIMESTAMP,
    FirmaInvalidaError,
    MotivoRechazo,
    VerificadorFirma,
    cabeceras_firmadas,
    firmar,
    mensaje_canonico,
)
from tests.conftest import SECRETO_PRUEBA

TS = "1760000000"


@pytest.mark.parametrize(
    ("metodo", "ruta", "cuerpo", "esperada"),
    [
        (
            "GET",
            "/api/v1/status",
            b"",
            "fcd686a749c71724bde4a22b49a4f0efb6804679c254cb1666ddbf112c023f49",
        ),
        (
            "POST",
            "/v1/diagnostico/benchmark",
            b'{"modelos":["tiny"]}',
            "79b879931374cba8459f058a45e64a75ca976a02f3c9d5fa1fc2764db1e5e7dc",
        ),
        ("GET", "/health", b"", "4db3ff880b724cc566f52626e2f1315b187eae83d8ef69b271079ad3df3eee7c"),
    ],
)
def test_vectores_compartidos_con_backend_y_bff(metodo, ruta, cuerpo, esperada):
    assert firmar(SECRETO_PRUEBA, TS, metodo, ruta, cuerpo) == esperada


def test_mensaje_canonico_normaliza_el_metodo_a_mayusculas():
    assert mensaje_canonico(TS, "get", "/x", b"").split("\n")[1] == "GET"


def _verificador(ahora: float = 1760000000.0) -> VerificadorFirma:
    return VerificadorFirma(SECRETO_PRUEBA, tolerancia_segundos=300, reloj=lambda: ahora)


def test_acepta_una_firma_valida():
    firma = firmar(SECRETO_PRUEBA, TS, "POST", "/r", b"{}")
    _verificador().verificar(TS, firma, "POST", "/r", b"{}")


def test_acepta_la_firma_en_mayusculas():
    firma = firmar(SECRETO_PRUEBA, TS, "GET", "/r", b"").upper()
    _verificador().verificar(TS, firma, "GET", "/r", b"")


@pytest.mark.parametrize(("ts", "firma"), [(None, "abc"), (TS, None), ("", "abc")])
def test_rechaza_si_falta_alguna_cabecera(ts, firma):
    with pytest.raises(FirmaInvalidaError) as exc:
        _verificador().verificar(ts, firma, "GET", "/r", b"")
    assert exc.value.motivo is MotivoRechazo.FALTA_CABECERA


@pytest.mark.parametrize("ts", ["abc", "-5", "1.5", "9999999999999"])
def test_rechaza_timestamps_no_numericos_o_absurdos(ts):
    with pytest.raises(FirmaInvalidaError) as exc:
        _verificador().verificar(ts, "abc", "GET", "/r", b"")
    assert exc.value.motivo is MotivoRechazo.TIMESTAMP_INVALIDO


@pytest.mark.parametrize("desfase", [301, -301, 3600])
def test_rechaza_firmas_fuera_de_la_ventana(desfase):
    firma = firmar(SECRETO_PRUEBA, TS, "GET", "/r", b"")
    with pytest.raises(FirmaInvalidaError) as exc:
        _verificador(1760000000.0 + desfase).verificar(TS, firma, "GET", "/r", b"")
    assert exc.value.motivo is MotivoRechazo.FUERA_DE_VENTANA


def test_acepta_justo_en_el_borde_de_la_ventana():
    firma = firmar(SECRETO_PRUEBA, TS, "GET", "/r", b"")
    _verificador(1760000300.0).verificar(TS, firma, "GET", "/r", b"")


@pytest.mark.parametrize(
    ("metodo", "ruta", "cuerpo"),
    [("POST", "/r", b'{"a":2}'), ("POST", "/otra", b'{"a":1}'), ("PUT", "/r", b'{"a":1}')],
)
def test_rechaza_si_se_altera_metodo_ruta_o_cuerpo(metodo, ruta, cuerpo):
    firma = firmar(SECRETO_PRUEBA, TS, "POST", "/r", b'{"a":1}')
    with pytest.raises(FirmaInvalidaError) as exc:
        _verificador().verificar(TS, firma, metodo, ruta, cuerpo)
    assert exc.value.motivo is MotivoRechazo.FIRMA_INCORRECTA


def test_rechaza_firma_hecha_con_otro_secreto():
    firma = firmar("otro-secreto-distinto-de-al-menos-32-caracteres", TS, "GET", "/r", b"")
    with pytest.raises(FirmaInvalidaError):
        _verificador().verificar(TS, firma, "GET", "/r", b"")


def test_cabeceras_firmadas_producen_una_firma_verificable():
    cab = cabeceras_firmadas(SECRETO_PRUEBA, "GET", "/r", b"", ahora=1760000000)
    assert cab[CABECERA_TIMESTAMP] == TS
    _verificador().verificar(cab[CABECERA_TIMESTAMP], cab[CABECERA_FIRMA], "GET", "/r", b"")
