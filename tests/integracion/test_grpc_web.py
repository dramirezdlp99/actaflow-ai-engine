"""Motor real por gRPC-Web (HTTP/1.1), el transporte de produccion en Render Free."""

from __future__ import annotations

import base64
import urllib.request

import pytest
from google.rpc import status_pb2

from actaflow.common.v1 import errors_pb2
from actaflow.engine.v1 import engine_pb2
from actaflow.system.v1 import service_status_pb2 as estado_pb
from actaflow_engine.rpc import tramas
from actaflow_engine.rpc.cliente_web import GrpcWebError, llamar
from actaflow_engine.seguridad.hmac_firma import metadatos_firmados
from tests.conftest import SECRETO_PRUEBA, crear_modelo_falso

ESTADO = "/actaflow.system.v1.ServiceStatusService/GetServiceStatus"
BENCHMARK = "/actaflow.engine.v1.EngineDiagnosticsService/RunBenchmark"


def post_crudo(url, ruta, cuerpo, cabeceras):
    solicitud = urllib.request.Request(
        f"{url}{ruta}", data=cuerpo, headers=cabeceras, method="POST"
    )
    with urllib.request.urlopen(solicitud, timeout=10) as respuesta:  # noqa: S310
        return respuesta.status, dict(respuesta.headers), respuesta.read()


def trailers(cuerpo):
    for trama in tramas.decodificar(cuerpo, 1 << 20):
        if trama.es_trailers:
            return tramas.leer_trailers(trama.contenido)
    return {}


def test_estado_por_grpc_web_informa_el_transporte(motor, models_dir):
    crear_modelo_falso(models_dir, "tiny")
    respuesta = llamar(
        motor.url_web,
        ESTADO,
        estado_pb.GetServiceStatusRequest(),
        estado_pb.GetServiceStatusResponse,
        SECRETO_PRUEBA,
    )
    assert respuesta.status.served_via == estado_pb.TRANSPORT_GRPC_WEB
    assert respuesta.status.components[0].state == estado_pb.HEALTH_STATE_OK


def test_el_cliente_no_puede_fingir_el_transporte(motor):
    cuerpo = b""
    cabeceras = {"Content-Type": "application/grpc-web+proto", "x-actaflow-transport": "grpc"}
    cabeceras.update(dict(metadatos_firmados(SECRETO_PRUEBA, ESTADO, cuerpo)))
    _, _, datos = post_crudo(motor.url_web, ESTADO, tramas.trama_datos(cuerpo), cabeceras)
    mensajes = [t.contenido for t in tramas.decodificar(datos, 1 << 20) if not t.es_trailers]
    respuesta = estado_pb.GetServiceStatusResponse.FromString(mensajes[0])
    assert respuesta.status.served_via == estado_pb.TRANSPORT_GRPC_WEB


def test_sin_firma_el_error_viaja_en_los_trailers(motor):
    status, cabeceras, cuerpo = post_crudo(
        motor.url_web,
        ESTADO,
        tramas.trama_datos(b""),
        {"Content-Type": "application/grpc-web+proto"},
    )
    assert status == 200
    assert cabeceras["content-type"] == "application/grpc-web+proto"
    assert trailers(cuerpo) == {"grpc-status": "16", "grpc-message": "Llamada no autorizada"}


def test_las_violaciones_del_contrato_llegan_tipadas_por_grpc_web(motor):
    peticion = engine_pb2.RunBenchmarkRequest(models=[1, 1])
    with pytest.raises(GrpcWebError) as exc:
        llamar(motor.url_web, BENCHMARK, peticion, engine_pb2.RunBenchmarkResponse, SECRETO_PRUEBA)
    assert exc.value.codigo == 3
    valor = exc.value.trailers["grpc-status-details-bin"]
    estado = status_pb2.Status.FromString(base64.b64decode(valor + "=" * (-len(valor) % 4)))
    violaciones = errors_pb2.FieldViolations()
    estado.details[0].Unpack(violaciones)
    assert violaciones.violations[0].rule == "repeated.unique"


def test_benchmark_por_grpc_web(motor, models_dir):
    crear_modelo_falso(models_dir, "tiny")
    peticion = engine_pb2.RunBenchmarkRequest(models=[engine_pb2.MODEL_SIZE_TINY])
    respuesta = llamar(
        motor.url_web, BENCHMARK, peticion, engine_pb2.RunBenchmarkResponse, SECRETO_PRUEBA
    )
    assert respuesta.results[0].outcome == engine_pb2.BENCHMARK_OUTCOME_OK


@pytest.mark.parametrize(
    ("ruta", "codigo"),
    [
        ("/actaflow.system.v1.NoExisteService/Metodo", "12"),
        ("/actaflow.engine.v1.TranscriptionService/StreamTranscription", "12"),
        ("/grpc.reflection.v1alpha.ServerReflection/ServerReflectionInfo", "12"),
    ],
)
def test_metodos_desconocidos_de_streaming_entrante_o_internos_no_se_publican(motor, ruta, codigo):
    _, _, cuerpo = post_crudo(
        motor.url_web, ruta, tramas.trama_datos(b""), {"Content-Type": "application/grpc-web+proto"}
    )
    assert trailers(cuerpo)["grpc-status"] == codigo


def test_tramas_malformadas_son_argumento_invalido(motor):
    _, _, cuerpo = post_crudo(
        motor.url_web, ESTADO, b"\x00\x00\x00", {"Content-Type": "application/grpc-web+proto"}
    )
    assert trailers(cuerpo)["grpc-status"] == "3"


def test_otro_tipo_de_contenido_es_415(motor):
    with pytest.raises(urllib.error.HTTPError) as exc:
        post_crudo(motor.url_web, ESTADO, b"{}", {"Content-Type": "application/json"})
    assert exc.value.code == 415


def test_cuerpo_mayor_al_limite_es_413(motor):
    with pytest.raises(urllib.error.HTTPError) as exc:
        post_crudo(
            motor.url_web,
            ESTADO,
            tramas.trama_datos(b"x" * 5000),
            {"Content-Type": "application/grpc-web+proto"},
        )
    assert exc.value.code == 413
