"""Motor real por gRPC nativo (HTTP/2): servicios, firma y reglas del contrato."""

from __future__ import annotations

import time

import grpc
import pytest
from google.rpc import status_pb2
from grpc_reflection.v1alpha import reflection_pb2, reflection_pb2_grpc

from actaflow.common.v1 import errors_pb2
from actaflow.engine.v1 import engine_pb2, engine_pb2_grpc
from actaflow.system.v1 import service_status_pb2 as estado_pb
from actaflow.system.v1 import service_status_pb2_grpc
from actaflow_engine.seguridad.hmac_firma import metadatos_firmados
from tests.conftest import SECRETO_PRUEBA, crear_modelo_falso

ESTADO = "/actaflow.system.v1.ServiceStatusService/GetServiceStatus"
BENCHMARK = "/actaflow.engine.v1.EngineDiagnosticsService/RunBenchmark"


@pytest.fixture
def canal(motor):
    with grpc.insecure_channel(motor.destino_grpc) as canal:
        yield canal


def firmado(metodo, peticion, secreto=SECRETO_PRUEBA, ahora=None):
    return metadatos_firmados(secreto, metodo, peticion.SerializeToString(), ahora)


def test_estado_degradado_sin_modelo_y_llamado_por_grpc_nativo(canal):
    stub = service_status_pb2_grpc.ServiceStatusServiceStub(canal)
    peticion = estado_pb.GetServiceStatusRequest()
    estado = stub.GetServiceStatus(peticion, metadata=firmado(ESTADO, peticion)).status
    assert estado.service_name == "ai-engine"
    assert estado.state == estado_pb.HEALTH_STATE_DEGRADED
    assert estado.served_via == estado_pb.TRANSPORT_GRPC
    assert [c.id for c in estado.components] == ["speech-model", "nlp-model"]
    assert estado.components[0].detail == "Modelo de voz tiny no instalado"
    assert estado.checked_at.seconds > 0


def test_estado_del_modelo_listo_cuando_esta_instalado(canal, models_dir):
    crear_modelo_falso(models_dir, "tiny")
    stub = service_status_pb2_grpc.ServiceStatusServiceStub(canal)
    peticion = estado_pb.GetServiceStatusRequest()
    estado = stub.GetServiceStatus(peticion, metadata=firmado(ESTADO, peticion)).status
    voz = estado.components[0]
    assert voz.state == estado_pb.HEALTH_STATE_OK
    assert voz.detail == "Modelo de voz tiny listo"
    assert voz.version == "faster-whisper-tiny-int8"


@pytest.mark.parametrize(
    "metadatos",
    [
        [],
        firmado(
            ESTADO,
            estado_pb.GetServiceStatusRequest(),
            secreto="otro-secreto-de-al-menos-32-caracteres-x",
        ),
        firmado(ESTADO, estado_pb.GetServiceStatusRequest(), ahora=time.time() - 3600),
        firmado(BENCHMARK, estado_pb.GetServiceStatusRequest()),
    ],
    ids=["sin-firma", "otro-secreto", "firma-vieja", "firma-de-otro-metodo"],
)
def test_rechaza_llamadas_sin_firma_valida(canal, metadatos):
    stub = service_status_pb2_grpc.ServiceStatusServiceStub(canal)
    with pytest.raises(grpc.RpcError) as exc:
        stub.GetServiceStatus(estado_pb.GetServiceStatusRequest(), metadata=metadatos)
    assert exc.value.code() == grpc.StatusCode.UNAUTHENTICATED
    assert exc.value.details() == "Llamada no autorizada"


def test_la_firma_cubre_los_bytes_exactos_del_mensaje(canal):
    stub = engine_pb2_grpc.EngineDiagnosticsServiceStub(canal)
    firmada = engine_pb2.RunBenchmarkRequest(models=[engine_pb2.MODEL_SIZE_TINY])
    enviada = engine_pb2.RunBenchmarkRequest(models=[engine_pb2.MODEL_SIZE_SMALL])
    with pytest.raises(grpc.RpcError) as exc:
        stub.RunBenchmark(enviada, metadata=firmado(BENCHMARK, firmada))
    assert exc.value.code() == grpc.StatusCode.UNAUTHENTICATED


def test_aplica_las_reglas_del_contrato_con_detalles_tipados(canal):
    stub = engine_pb2_grpc.EngineDiagnosticsServiceStub(canal)
    peticion = engine_pb2.RunBenchmarkRequest(models=[1, 1])
    with pytest.raises(grpc.RpcError) as exc:
        stub.RunBenchmark(peticion, metadata=firmado(BENCHMARK, peticion))
    assert exc.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    detalles = dict(exc.value.trailing_metadata())["grpc-status-details-bin"]
    estado = status_pb2.Status.FromString(detalles)
    violaciones = errors_pb2.FieldViolations()
    assert estado.details[0].Unpack(violaciones)
    assert [(v.field, v.rule) for v in violaciones.violations] == [("models", "repeated.unique")]


def test_benchmark_firmado_devuelve_las_mediciones(canal, models_dir, ejecutor_ok):
    crear_modelo_falso(models_dir, "tiny")
    stub = engine_pb2_grpc.EngineDiagnosticsServiceStub(canal)
    peticion = engine_pb2.RunBenchmarkRequest(
        models=[engine_pb2.MODEL_SIZE_TINY, engine_pb2.MODEL_SIZE_BASE]
    )
    respuesta = stub.RunBenchmark(peticion, metadata=firmado(BENCHMARK, peticion))
    tiny, base = respuesta.results
    assert tiny.outcome == engine_pb2.BENCHMARK_OUTCOME_OK
    assert tiny.real_time_factor == pytest.approx(1.0)
    assert tiny.peak_memory_bytes == 250000000
    assert tiny.word_error_rate >= 0
    assert base.outcome == engine_pb2.BENCHMARK_OUTCOME_NOT_INSTALLED
    assert respuesta.limits.visible_cpus >= 1
    assert len(ejecutor_ok.comandos) == 1


def test_benchmark_sin_audio_de_prueba_es_precondicion_fallida(canal, audio_prueba):
    audio_prueba.unlink()
    stub = engine_pb2_grpc.EngineDiagnosticsServiceStub(canal)
    peticion = engine_pb2.RunBenchmarkRequest(models=[engine_pb2.MODEL_SIZE_TINY])
    with pytest.raises(grpc.RpcError) as exc:
        stub.RunBenchmark(peticion, metadata=firmado(BENCHMARK, peticion))
    assert exc.value.code() == grpc.StatusCode.FAILED_PRECONDITION


def test_los_servicios_aun_no_implementados_responden_unimplemented(canal):
    stub = engine_pb2_grpc.TranscriptionServiceStub(canal)
    peticion = engine_pb2.TranscribeSegmentRequest()
    with pytest.raises(grpc.RpcError) as exc:
        stub.TranscribeSegment(peticion, metadata=firmado("/x", peticion))
    assert exc.value.code() == grpc.StatusCode.UNIMPLEMENTED


def test_la_reflexion_describe_los_servicios_publicados(canal):
    stub = reflection_pb2_grpc.ServerReflectionStub(canal)
    respuesta = next(
        stub.ServerReflectionInfo(iter([reflection_pb2.ServerReflectionRequest(list_services="")]))
    )
    nombres = {s.name for s in respuesta.list_services_response.service}
    assert "actaflow.system.v1.ServiceStatusService" in nombres
    assert "actaflow.engine.v1.EngineDiagnosticsService" in nombres
