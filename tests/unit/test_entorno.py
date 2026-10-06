from __future__ import annotations

from pathlib import Path

import pytest

from actaflow_engine.diagnostico.entorno import leer_entorno, parsear_cpu_max, parsear_memoria_max


@pytest.mark.parametrize(
    ("contenido", "esperado"),
    [("536870912", 536870912), ("max", None), (None, None), ("basura", None)],
)
def test_parsear_memoria_max(contenido, esperado):
    assert parsear_memoria_max(contenido) == esperado


@pytest.mark.parametrize(
    ("contenido", "esperado"),
    [
        ("10000 100000", 0.1),
        ("50000 100000", 0.5),
        ("max 100000", None),
        ("", None),
        ("1 0", None),
        ("a b", None),
        ("10000", None),
    ],
)
def test_parsear_cpu_max(contenido, esperado):
    assert parsear_cpu_max(contenido) == esperado


def test_leer_entorno_desde_archivos_cgroup(tmp_path: Path):
    (tmp_path / "memory.max").write_text("536870912\n")
    (tmp_path / "cpu.max").write_text("10000 100000\n")
    entorno = leer_entorno(tmp_path)
    assert entorno.memoria_limite_bytes == 536870912
    assert entorno.cpu_cuota_nucleos == 0.1
    assert entorno.cpus_visibles >= 1


def test_leer_entorno_sin_cgroup_no_falla(tmp_path: Path):
    entorno = leer_entorno(tmp_path / "no-existe")
    assert entorno.memoria_limite_bytes is None
    assert entorno.cpu_cuota_nucleos is None
