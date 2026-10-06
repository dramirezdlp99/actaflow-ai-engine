"""Lectura de los limites reales del contenedor (cgroup v2): RAM y cuota de CPU.

Sirve para confirmar en produccion los limites del plan gratuito en lugar de suponerlos.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path

RAIZ_CGROUP = Path("/sys/fs/cgroup")


@dataclass(frozen=True)
class EntornoContenedor:
    memoria_limite_bytes: int | None
    cpu_cuota_nucleos: float | None
    cpus_visibles: int

    def como_dict(self) -> dict[str, object]:
        return asdict(self)


def _leer(ruta: Path) -> str | None:
    try:
        return ruta.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def parsear_memoria_max(contenido: str | None) -> int | None:
    if not contenido or contenido == "max":
        return None
    return int(contenido) if contenido.isdigit() else None


def parsear_cpu_max(contenido: str | None) -> float | None:
    """``cpu.max`` tiene la forma ``"<cuota> <periodo>"``, por ejemplo ``"10000 100000"``."""
    if not contenido:
        return None
    partes = contenido.split()
    if len(partes) != 2 or partes[0] == "max":
        return None
    try:
        return round(int(partes[0]) / int(partes[1]), 3)
    except (ValueError, ZeroDivisionError):
        return None


def leer_entorno(raiz: Path = RAIZ_CGROUP) -> EntornoContenedor:
    return EntornoContenedor(
        memoria_limite_bytes=parsear_memoria_max(_leer(raiz / "memory.max")),
        cpu_cuota_nucleos=parsear_cpu_max(_leer(raiz / "cpu.max")),
        cpus_visibles=os.cpu_count() or 1,
    )
