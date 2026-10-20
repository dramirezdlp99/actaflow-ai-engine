"""Transcriptor: decodificacion, limites y resultado, con un reconocedor simulado."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from actaflow_engine.voz.transcriptor import (
    AudioInvalidoError,
    ModeloNoDisponibleError,
    Transcriptor,
    decodificar,
    indicacion,
)
from tests.audio_prueba import ogg_opus, wav
from tests.conftest import crear_modelo_falso


class ReconocedorFalso:
    def __init__(self) -> None:
        self.llamadas: list[dict] = []

    def transcribe(self, audio, **opciones):  # noqa: ANN001, ANN003, ANN201
        self.llamadas.append({"muestras": len(audio), **opciones})
        segmentos = [
            SimpleNamespace(start=0.0, end=1.2, text=" Buenos días.", avg_logprob=-0.105),
            SimpleNamespace(start=1.2, end=1.4, text="  ", avg_logprob=-2.0),
            SimpleNamespace(start=1.4, end=9.0, text=" Inicia la audiencia.", avg_logprob=0.5),
        ]
        return iter(segmentos), SimpleNamespace(language="es")


def test_decodifica_wav_y_ogg_opus_a_16_khz():
    assert len(decodificar(wav(1.0))) == 16_000
    assert abs(len(decodificar(ogg_opus(2.0))) - 32_000) <= 160


@pytest.mark.parametrize(
    ("datos", "mensaje"),
    [(b"no es audio", "decodificar"), (wav(31.0), "30 segundos")],
    ids=["basura", "mas-de-30-s"],
)
def test_rechaza_audio_ilegible_o_largo(datos, mensaje):
    with pytest.raises(AudioInvalidoError, match=mensaje):
        decodificar(datos)


def test_indicacion_con_nombres_y_vocabulario():
    assert indicacion([], []) is None
    assert (
        indicacion(["Ana Ruiz"], ["convocante"])
        == "Participantes: Ana Ruiz. Vocabulario: convocante."
    )


def test_transcribe_con_el_modelo_cargado_una_sola_vez(tmp_path: Path):
    crear_modelo_falso(tmp_path, "tiny")
    falso = ReconocedorFalso()
    cargas: list[str] = []
    transcriptor = Transcriptor(
        tmp_path, "tiny", cargar=lambda carpeta: cargas.append(carpeta) or falso
    )
    resultado = transcriptor.transcribir(wav(2.0), nombres=["Ana Ruiz"])
    transcriptor.transcribir(wav(1.0))
    assert len(cargas) == 1 and cargas[0].endswith("faster-whisper-tiny")
    assert resultado.modelo == "faster-whisper-tiny-int8"
    assert resultado.duracion_ms == 2000
    assert [(t.inicio_ms, t.fin_ms, t.texto, t.confianza) for t in resultado.tramos] == [
        (0, 1200, "Buenos días.", 0.9),
        (1400, 2000, "Inicia la audiencia.", 1.0),
    ]
    opciones = falso.llamadas[0]
    assert (opciones["language"], opciones["vad_filter"], opciones["muestras"]) == (
        "es",
        False,
        32_000,
    )
    assert opciones["initial_prompt"] == "Participantes: Ana Ruiz."


def test_sin_modelo_instalado(tmp_path: Path):
    transcriptor = Transcriptor(tmp_path, "tiny", cargar=lambda _: ReconocedorFalso())
    with pytest.raises(ModeloNoDisponibleError, match="no instalado"):
        transcriptor.transcribir(wav(1.0))
