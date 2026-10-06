from __future__ import annotations

from pathlib import Path

from actaflow_engine.inventario import asr_disponibles, inventario
from tests.conftest import crear_modelo_falso


def test_solo_cuenta_carpetas_con_model_bin(models_dir: Path):
    crear_modelo_falso(models_dir, "tiny")
    (models_dir / "faster-whisper-base").mkdir()  # carpeta vacia: descarga incompleta
    assert asr_disponibles(models_dir) == ["tiny"]


def test_ignora_modelos_no_soportados(models_dir: Path):
    crear_modelo_falso(models_dir, "large-v3")
    assert asr_disponibles(models_dir) == []


def test_asr_listo_solo_si_el_configurado_esta_instalado(models_dir: Path):
    crear_modelo_falso(models_dir, "tiny")
    assert inventario(models_dir, "tiny").asr_listo
    assert not inventario(models_dir, "base").asr_listo
