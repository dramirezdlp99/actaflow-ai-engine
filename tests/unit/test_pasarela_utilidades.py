from __future__ import annotations

import pytest

from actaflow_engine.main import destino_local
from actaflow_engine.rpc import METADATO_TRANSPORTE, TRANSPORTE_GRPC_WEB
from actaflow_engine.rpc.pasarela import (
    RUTA_VALIDA,
    TIEMPO_POR_DEFECTO_S,
    metadatos_reenviados,
    plazo,
)


@pytest.mark.parametrize(
    ("cabecera", "segundos"),
    [
        ("30S", 30.0),
        ("500m", 0.5),
        ("2M", 120.0),
        ("1H", TIEMPO_POR_DEFECTO_S),
        (None, TIEMPO_POR_DEFECTO_S),
        ("abc", TIEMPO_POR_DEFECTO_S),
        ("10x", TIEMPO_POR_DEFECTO_S),
        ("S", TIEMPO_POR_DEFECTO_S),
    ],
)
def test_plazo_interpreta_grpc_timeout_con_un_maximo(cabecera, segundos):
    assert plazo(cabecera) == pytest.approx(segundos)


def test_solo_reenvia_firma_y_sesion_y_el_transporte_lo_pone_la_pasarela():
    reenviados = metadatos_reenviados(
        {
            "x-actaflow-timestamp": "1",
            "x-actaflow-signature": "f",
            "authorization": "Bearer t",
            "cookie": "secreta",
            "host": "x",
            METADATO_TRANSPORTE: "grpc",
        }
    )
    assert dict(reenviados) == {
        "x-actaflow-timestamp": "1",
        "x-actaflow-signature": "f",
        "authorization": "Bearer t",
        METADATO_TRANSPORTE: TRANSPORTE_GRPC_WEB,
    }


@pytest.mark.parametrize(
    ("ruta", "valida"),
    [
        ("/actaflow.system.v1.ServiceStatusService/GetServiceStatus", True),
        ("/actaflow.engine.v1.EngineDiagnosticsService/RunBenchmark", True),
        ("/grpc.reflection.v1alpha.ServerReflection/ServerReflectionInfo", False),
        ("/health", False),
        ("/actaflow.system.v1.ServiceStatusService/../x", False),
    ],
)
def test_solo_se_publican_servicios_de_actaflow(ruta, valida):
    assert (RUTA_VALIDA.match(ruta) is not None) is valida


@pytest.mark.parametrize(
    ("bind", "destino"),
    [
        ("127.0.0.1:8102", "127.0.0.1:9"),
        ("0.0.0.0:8102", "127.0.0.1:9"),
        ("[::]:8102", "127.0.0.1:9"),
    ],
)
def test_la_pasarela_llega_al_servidor_por_la_interfaz_local(bind, destino):
    assert destino_local(bind, 9) == destino
