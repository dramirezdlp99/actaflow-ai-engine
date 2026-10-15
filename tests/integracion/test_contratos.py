"""El codigo generado debe corresponder exactamente a la version fijada de los contratos."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def _cargar_generador():
    especificacion = importlib.util.spec_from_file_location(
        "generar_contratos", RAIZ / "scripts" / "generar_contratos.py"
    )
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


def test_el_codigo_generado_esta_al_dia_con_contracts():
    assert _cargar_generador().comprobar() == []


def test_el_lock_apunta_al_repositorio_de_contratos_y_a_una_version_publicada():
    lock = json.loads((RAIZ / "contracts.lock.json").read_text(encoding="utf-8"))
    assert lock["repository"] == "https://github.com/dramirezdlp99/actaflow-contracts.git"
    assert lock["version"].startswith("v")
    assert "actaflow/engine/v1/engine.proto" in lock["files"]
