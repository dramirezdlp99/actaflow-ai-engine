from __future__ import annotations

import pytest
from pydantic import ValidationError

from actaflow_engine.config import Settings
from tests.conftest import SECRETO_PRUEBA


def test_rechaza_secretos_cortos():
    with pytest.raises(ValidationError, match="32 caracteres"):
        Settings(hmac_secret="corto", _env_file=None)


def test_rechaza_modelos_asr_no_soportados():
    with pytest.raises(ValidationError, match="no soportado"):
        Settings(hmac_secret=SECRETO_PRUEBA, asr_model="large-v3", _env_file=None)


def test_lee_la_configuracion_de_variables_de_entorno(monkeypatch):
    monkeypatch.setenv("ACTAFLOW_ENGINE_HMAC_SECRET", SECRETO_PRUEBA)
    monkeypatch.setenv("ACTAFLOW_ENGINE_ENVIRONMENT", "produccion")
    monkeypatch.setenv("ACTAFLOW_ENGINE_ASR_MODEL", "base")
    settings = Settings(_env_file=None)
    assert settings.es_produccion
    assert settings.asr_model == "base"


def test_el_secreto_no_aparece_al_imprimir_la_configuracion():
    settings = Settings(hmac_secret=SECRETO_PRUEBA, _env_file=None)
    assert SECRETO_PRUEBA not in repr(settings)
