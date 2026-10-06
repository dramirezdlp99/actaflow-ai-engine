from __future__ import annotations

import json
import time

from fastapi.testclient import TestClient

from actaflow_engine.api import diagnostico
from actaflow_engine.seguridad.hmac_firma import cabeceras_firmadas
from tests.conftest import SECRETO_PRUEBA, crear_modelo_falso

RUTA = "/v1/diagnostico/benchmark"


def _post_firmado(
    cliente: TestClient,
    cuerpo: dict | bytes,
    secreto: str = SECRETO_PRUEBA,
    ahora: float | None = None,
):
    datos = cuerpo if isinstance(cuerpo, bytes) else json.dumps(cuerpo).encode()
    cabeceras = {"Content-Type": "application/json"}
    cabeceras.update(cabeceras_firmadas(secreto, "POST", RUTA, datos, ahora=ahora))
    return cliente.post(RUTA, content=datos, headers=cabeceras)


def test_sin_firma_responde_401_sin_dar_pistas(cliente: TestClient):
    resp = cliente.post(RUTA, json={"modelos": ["tiny"]})
    assert resp.status_code == 401
    assert resp.json() == {
        "estado": 401,
        "codigo": "firma_invalida",
        "mensaje": "Peticion no autorizada",
    }


def test_firma_con_otro_secreto_responde_401(cliente: TestClient):
    resp = _post_firmado(
        cliente, {"modelos": ["tiny"]}, secreto="secreto-equivocado-pero-suficientemente-largo-xx"
    )
    assert resp.status_code == 401


def test_firma_vieja_responde_401(cliente: TestClient):
    resp = _post_firmado(cliente, {"modelos": ["tiny"]}, ahora=time.time() - 3600)
    assert resp.status_code == 401


def test_cuerpo_alterado_despues_de_firmar_responde_401(cliente: TestClient):
    original = json.dumps({"modelos": ["tiny"]}).encode()
    cabeceras = cabeceras_firmadas(SECRETO_PRUEBA, "POST", RUTA, original)
    cabeceras["Content-Type"] = "application/json"
    resp = cliente.post(
        RUTA, content=json.dumps({"modelos": ["small"]}).encode(), headers=cabeceras
    )
    assert resp.status_code == 401


def test_benchmark_firmado_devuelve_el_informe(cliente: TestClient, models_dir, ejecutor_ok):
    crear_modelo_falso(models_dir, "tiny")
    resp = _post_firmado(cliente, {"modelos": ["tiny", "base"]})
    assert resp.status_code == 200
    datos = resp.json()
    estados = {r["modelo"]: r["estado"] for r in datos["resultados"]}
    assert estados == {"tiny": "ok", "base": "no_instalado"}
    assert datos["resultados"][0]["wer"] is not None
    assert "entorno" in datos
    assert len(ejecutor_ok.comandos) == 1


def test_modelos_invalidos_o_repetidos_dan_422(cliente: TestClient):
    for cuerpo in ({"modelos": ["large-v3"]}, {"modelos": ["tiny", "tiny"]}, {"modelos": []}):
        resp = _post_firmado(cliente, cuerpo)
        assert resp.status_code == 422, cuerpo
        assert resp.json()["codigo"] == "solicitud_invalida"


def test_sin_audio_de_prueba_responde_409(cliente: TestClient, audio_prueba):
    audio_prueba.unlink()
    resp = _post_firmado(cliente, {"modelos": ["tiny"]})
    assert resp.status_code == 409
    assert resp.json()["codigo"] == "audio_no_disponible"


def test_solo_un_benchmark_a_la_vez(cliente: TestClient):
    assert diagnostico._candado.acquire(blocking=False)
    try:
        resp = _post_firmado(cliente, {"modelos": ["tiny"]})
    finally:
        diagnostico._candado.release()
    assert resp.status_code == 409
    assert resp.json()["codigo"] == "benchmark_en_curso"


def test_cuerpo_mayor_al_limite_responde_413(cliente: TestClient):
    enorme = json.dumps({"modelos": ["tiny"], "relleno": "x" * 5000}).encode()
    resp = _post_firmado(cliente, enorme)
    assert resp.status_code == 413
    assert resp.json()["codigo"] == "cuerpo_demasiado_grande"


def test_guion_de_referencia_esta_empaquetado():
    guion = diagnostico.guion_referencia()
    assert "audiencia de conciliación" in guion
    assert "un millón quinientos mil pesos" in guion
