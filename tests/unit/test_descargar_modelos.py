from __future__ import annotations

from pathlib import Path

import pytest

from actaflow_engine.herramientas.descargar_modelos import descargar


def _descargador_falso(nombre: str, destino: str) -> str:
    (Path(destino) / "model.bin").write_bytes(b"falso")
    return destino


def test_descarga_cada_modelo_en_su_carpeta(tmp_path: Path):
    rutas = descargar(["tiny", "base"], tmp_path, _descargador_falso)
    assert [r.name for r in rutas] == ["faster-whisper-tiny", "faster-whisper-base"]
    assert all((r / "model.bin").is_file() for r in rutas)


def test_rechaza_modelos_no_soportados_antes_de_descargar(tmp_path: Path):
    llamados = []
    with pytest.raises(ValueError, match="no soportados"):
        descargar(["tiny", "large-v3"], tmp_path, lambda n, d: llamados.append(n) or d)
    assert llamados == []


def test_falla_si_la_descarga_no_deja_model_bin(tmp_path: Path):
    with pytest.raises(RuntimeError, match="model.bin"):
        descargar(["tiny"], tmp_path, lambda n, d: d)
