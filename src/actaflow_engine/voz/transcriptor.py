"""Transcripcion de segmentos de audio con faster-whisper (CPU, int8).

El modelo se carga una sola vez, en el primer uso, y las transcripciones van de una en una: en
Render Free hay una sola CPU y 512 MB, y dos a la vez solo se estorbarian.
"""

from __future__ import annotations

import io
import math
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

FRECUENCIA = 16_000
MAX_SEGUNDOS = 30.5  # el contrato: un segmento es una intervencion de hasta 30 s


class AudioInvalidoError(Exception):
    """El audio no se pudo decodificar o es demasiado largo."""


class ModeloNoDisponibleError(Exception):
    """El modelo de voz configurado no esta instalado."""


@dataclass(frozen=True)
class Tramo:
    inicio_ms: int
    fin_ms: int
    texto: str
    confianza: float


@dataclass(frozen=True)
class Transcripcion:
    tramos: list[Tramo]
    duracion_ms: int
    factor_tiempo_real: float
    modelo: str


class Reconocedor(Protocol):
    """Lo minimo de faster_whisper.WhisperModel que se usa (asi las pruebas lo pueden simular)."""

    def transcribe(self, audio, **opciones): ...  # noqa: ANN001, ANN003, ANN201


def decodificar(datos: bytes) -> Sequence[float]:
    """Ogg Opus o WAV a muestras mono de 16 kHz."""
    from faster_whisper.audio import decode_audio

    try:
        audio = decode_audio(io.BytesIO(datos), sampling_rate=FRECUENCIA)
    except Exception as error:  # noqa: BLE001 - PyAV lanza muchos tipos distintos
        raise AudioInvalidoError("El audio no se pudo decodificar") from error
    if len(audio) == 0:
        raise AudioInvalidoError("El audio esta vacio")
    if len(audio) / FRECUENCIA > MAX_SEGUNDOS:
        raise AudioInvalidoError("El segmento supera 30 segundos")
    return audio


def indicacion(nombres: Sequence[str], vocabulario: Sequence[str]) -> str | None:
    """Texto inicial que orienta al modelo hacia los nombres propios y el vocabulario juridico."""
    partes = []
    if nombres:
        partes.append("Participantes: " + ", ".join(nombres) + ".")
    if vocabulario:
        partes.append("Vocabulario: " + ", ".join(vocabulario) + ".")
    return " ".join(partes)[:800] or None


class Transcriptor:
    def __init__(
        self,
        models_dir: Path,
        modelo: str,
        cargar: Callable[[str], Reconocedor] | None = None,
    ) -> None:
        self._carpeta = models_dir / f"faster-whisper-{modelo}"
        self.nombre_modelo = f"faster-whisper-{modelo}-int8"
        self._cargar = cargar or self._cargar_whisper
        self._modelo: Reconocedor | None = None
        self._candado = threading.Lock()

    @staticmethod
    def _cargar_whisper(carpeta: str) -> Reconocedor:
        from faster_whisper import WhisperModel

        return WhisperModel(
            carpeta, device="cpu", compute_type="int8", cpu_threads=2, num_workers=1
        )

    def _reconocedor(self) -> Reconocedor:
        if self._modelo is None:
            if not (self._carpeta / "model.bin").is_file():
                raise ModeloNoDisponibleError(f"Modelo de voz no instalado en {self._carpeta.name}")
            self._modelo = self._cargar(str(self._carpeta))
        return self._modelo

    def transcribir(
        self, datos: bytes, nombres: Sequence[str] = (), vocabulario: Sequence[str] = ()
    ) -> Transcripcion:
        """Transcribe un segmento. Bloqueante: llamar con asyncio.to_thread."""
        audio = decodificar(datos)
        duracion_ms = round(len(audio) * 1000 / FRECUENCIA)
        with self._candado:
            modelo = self._reconocedor()
            inicio = time.perf_counter()
            segmentos, _ = modelo.transcribe(
                audio,
                language="es",
                beam_size=1,
                vad_filter=False,  # el navegador ya corta por actividad de voz
                condition_on_previous_text=False,
                initial_prompt=indicacion(nombres, vocabulario),
            )
            tramos = [
                Tramo(
                    inicio_ms=max(0, round(s.start * 1000)),
                    fin_ms=min(duracion_ms, round(s.end * 1000)),
                    texto=s.text.strip(),
                    confianza=round(min(1.0, max(0.0, math.exp(s.avg_logprob))), 3),
                )
                for s in segmentos
                if s.text.strip()
            ]
            transcurrido = time.perf_counter() - inicio
        return Transcripcion(
            tramos=tramos,
            duracion_ms=duracion_ms,
            factor_tiempo_real=round(transcurrido / max(duracion_ms / 1000, 0.001), 3),
            modelo=self.nombre_modelo,
        )
