from __future__ import annotations

from fastapi.testclient import TestClient

from actaflow_engine import __version__
from actaflow_engine.config import Settings
from actaflow_engine.main import create_app
from tests.conftest import SECRETO_PRUEBA, crear_modelo_falso


def test_health_degradado_si_el_modelo_configurado_no_esta(cliente: TestClient):
    resp = cliente.get("/health")
    assert resp.status_code == 200
    datos = resp.json()
    assert datos["servicio"] == "actaflow-ai-engine"
    assert datos["version"] == __version__
    assert datos["estado"] == "degradado"
    assert datos["modelos"]["asr"] == {"configurado": "tiny", "disponibles": [], "listo": False}


def test_health_ok_y_lista_los_modelos_instalados(cliente: TestClient, models_dir):
    crear_modelo_falso(models_dir, "tiny")
    crear_modelo_falso(models_dir, "base")
    datos = cliente.get("/health").json()
    assert datos["estado"] == "ok"
    assert datos["modelos"]["asr"]["disponibles"] == ["tiny", "base"]
    assert isinstance(datos["modelos"]["nlp"]["disponibles"], list)


def test_health_no_necesita_firma_y_lleva_cabeceras_de_seguridad(cliente: TestClient):
    resp = cliente.get("/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["cache-control"] == "no-store"
    assert "server" not in resp.headers


def test_ruta_inexistente_devuelve_error_uniforme(cliente: TestClient):
    resp = cliente.get("/no-existe")
    assert resp.status_code == 404
    assert resp.json() == {"estado": 404, "codigo": "no_encontrado", "mensaje": "Not Found"}


def test_en_produccion_no_se_publica_la_documentacion(models_dir, audio_prueba):
    settings = Settings(
        hmac_secret=SECRETO_PRUEBA,
        environment="produccion",
        models_dir=models_dir,
        benchmark_audio=audio_prueba,
        _env_file=None,
    )
    cliente = TestClient(create_app(settings))
    assert cliente.get("/docs").status_code == 404
    assert cliente.get("/openapi.json").status_code == 404
    assert "default-src 'none'" in cliente.get("/health").headers["content-security-policy"]


def test_en_local_si_hay_documentacion(cliente: TestClient):
    assert cliente.get("/openapi.json").status_code == 200
