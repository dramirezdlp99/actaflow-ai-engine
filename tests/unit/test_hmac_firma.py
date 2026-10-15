from __future__ import annotations

import pytest

from actaflow.engine.v1 import engine_pb2
from actaflow_engine.seguridad.hmac_firma import (
    METADATO_FIRMA,
    METADATO_TIMESTAMP,
    FirmaInvalidaError,
    MotivoRechazo,
    VerificadorFirma,
    firmar,
    mensaje_canonico,
    metadatos_firmados,
)
from tests.conftest import SECRETO_PRUEBA

TS = "1760000000"
ESTADO = "/actaflow.system.v1.ServiceStatusService/GetServiceStatus"
BENCHMARK = "/actaflow.engine.v1.EngineDiagnosticsService/RunBenchmark"
FLUJO = "/actaflow.engine.v1.TranscriptionService/StreamTranscription"


def test_el_mensaje_de_benchmark_se_serializa_igual_que_en_los_otros_lenguajes():
    peticion = engine_pb2.RunBenchmarkRequest(models=[engine_pb2.MODEL_SIZE_TINY])
    assert peticion.SerializeToString().hex() == "0a0101"


@pytest.mark.parametrize(
    ("metodo", "cuerpo", "esperada"),
    [
        (ESTADO, b"", "2464942d647557cdabd41b2f6cdc7dcb23a204184913160c1e5df4d7c284778d"),
        (
            BENCHMARK,
            bytes.fromhex("0a0101"),
            "a58c8e638550007e92cb44c0e022ebe86c6fd260c7a310750a3080af78866cd3",
        ),
        (FLUJO, b"", "4c49b46fc8ed57ee5358b19be415110fbc39e3c74493f9ccf522de2401bf86e0"),
    ],
)
def test_vectores_compartidos_con_el_bff_y_los_microservicios(metodo, cuerpo, esperada):
    assert firmar(SECRETO_PRUEBA, TS, metodo, cuerpo) == esperada


def test_el_mensaje_canonico_marca_que_es_una_llamada_rpc():
    assert mensaje_canonico(TS, ESTADO, b"") == (
        f"{TS}\nRPC\n{ESTADO}\ne3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )


def _verificador(ahora: float = 1760000000.0) -> VerificadorFirma:
    return VerificadorFirma(SECRETO_PRUEBA, tolerancia_segundos=300, reloj=lambda: ahora)


def test_acepta_una_firma_valida_aunque_venga_en_mayusculas():
    firma = firmar(SECRETO_PRUEBA, TS, BENCHMARK, b"\x0a\x01\x01").upper()
    _verificador().verificar(TS, firma, BENCHMARK, b"\x0a\x01\x01")


@pytest.mark.parametrize(("ts", "firma"), [(None, "abc"), (TS, None), ("", "abc")])
def test_rechaza_si_falta_algun_metadato(ts, firma):
    with pytest.raises(FirmaInvalidaError) as exc:
        _verificador().verificar(ts, firma, ESTADO, b"")
    assert exc.value.motivo is MotivoRechazo.FALTA_METADATO


@pytest.mark.parametrize("ts", ["abc", "-5", "1.5", "9999999999999"])
def test_rechaza_timestamps_no_numericos_o_absurdos(ts):
    with pytest.raises(FirmaInvalidaError) as exc:
        _verificador().verificar(ts, "abc", ESTADO, b"")
    assert exc.value.motivo is MotivoRechazo.TIMESTAMP_INVALIDO


@pytest.mark.parametrize("desfase", [301, -301, 3600])
def test_rechaza_firmas_fuera_de_la_ventana(desfase):
    firma = firmar(SECRETO_PRUEBA, TS, ESTADO, b"")
    with pytest.raises(FirmaInvalidaError) as exc:
        _verificador(1760000000.0 + desfase).verificar(TS, firma, ESTADO, b"")
    assert exc.value.motivo is MotivoRechazo.FUERA_DE_VENTANA


def test_acepta_justo_en_el_borde_de_la_ventana():
    firma = firmar(SECRETO_PRUEBA, TS, ESTADO, b"")
    _verificador(1760000300.0).verificar(TS, firma, ESTADO, b"")


@pytest.mark.parametrize(
    ("metodo", "cuerpo"),
    [(BENCHMARK, b"\x0a\x01\x02"), (ESTADO, b"\x0a\x01\x01"), (FLUJO, b"\x0a\x01\x01")],
)
def test_rechaza_si_se_altera_el_metodo_o_los_bytes(metodo, cuerpo):
    firma = firmar(SECRETO_PRUEBA, TS, BENCHMARK, b"\x0a\x01\x01")
    with pytest.raises(FirmaInvalidaError) as exc:
        _verificador().verificar(TS, firma, metodo, cuerpo)
    assert exc.value.motivo is MotivoRechazo.FIRMA_INCORRECTA


def test_metadatos_firmados_producen_una_firma_verificable():
    metadatos = dict(metadatos_firmados(SECRETO_PRUEBA, ESTADO, b"", ahora=1760000000))
    assert metadatos[METADATO_TIMESTAMP] == TS
    _verificador().verificar(metadatos[METADATO_TIMESTAMP], metadatos[METADATO_FIRMA], ESTADO, b"")
