"""Regresion: la decodificacion de audio de faster-whisper debe funcionar con la version de
`av` instalada. Con av 19, faster-whisper 1.2.1 fallaba en produccion con
"open() got an unexpected keyword argument 'metadata_errors'"."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from faster_whisper.audio import decode_audio

FRECUENCIA = 16_000


def _wav_tono(ruta: Path, segundos: float = 1.0, frecuencia_muestreo: int = FRECUENCIA) -> Path:
    muestras = int(segundos * frecuencia_muestreo)
    with wave.open(str(ruta), "wb") as archivo:
        archivo.setnchannels(1)
        archivo.setsampwidth(2)
        archivo.setframerate(frecuencia_muestreo)
        archivo.writeframes(
            b"".join(
                struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / frecuencia_muestreo)))
                for i in range(muestras)
            )
        )
    return ruta


def test_decodifica_un_wav_como_lo_hace_whisper(tmp_path: Path):
    audio = decode_audio(str(_wav_tono(tmp_path / "tono.wav")))
    assert len(audio) == FRECUENCIA  # 1 s a 16 kHz


def test_remuestrea_a_16_khz_un_wav_de_22050_hz_como_el_de_espeak(tmp_path: Path):
    ruta = _wav_tono(tmp_path / "espeak.wav", segundos=2.0, frecuencia_muestreo=22_050)
    audio = decode_audio(str(ruta))
    assert abs(len(audio) - 2 * FRECUENCIA) <= 16
