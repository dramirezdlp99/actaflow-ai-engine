"""Inventario de modelos instalados, sin cargarlos en memoria."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path

from actaflow_engine.config import MODELOS_ASR_SOPORTADOS

MODELOS_NLP_CONOCIDOS: tuple[str, ...] = ("es_core_news_sm", "es_core_news_md")


def carpeta_modelo_asr(models_dir: Path, nombre: str) -> Path:
    return models_dir / f"faster-whisper-{nombre}"


def asr_disponibles(models_dir: Path) -> list[str]:
    """Modelos de faster-whisper presentes en disco (carpeta con model.bin)."""
    return [
        nombre
        for nombre in MODELOS_ASR_SOPORTADOS
        if (carpeta_modelo_asr(models_dir, nombre) / "model.bin").is_file()
    ]


def nlp_disponibles() -> list[str]:
    """Paquetes de spaCy en espanol instalados (solo se comprueba que existan)."""
    return [nombre for nombre in MODELOS_NLP_CONOCIDOS if importlib.util.find_spec(nombre)]


@dataclass(frozen=True)
class Inventario:
    asr_configurado: str
    asr_disponibles: list[str]
    nlp_disponibles: list[str]

    @property
    def asr_listo(self) -> bool:
        return self.asr_configurado in self.asr_disponibles


def inventario(models_dir: Path, asr_configurado: str) -> Inventario:
    return Inventario(
        asr_configurado=asr_configurado,
        asr_disponibles=asr_disponibles(models_dir),
        nlp_disponibles=nlp_disponibles(),
    )
