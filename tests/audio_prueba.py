"""Audio sintetico para las pruebas: WAV PCM 16 kHz y Ogg Opus (lo que produce el navegador)."""

from __future__ import annotations

import io
import math
import struct
import wave

import av
import numpy as np


def wav(segundos: float, frecuencia: int = 16_000) -> bytes:
    salida = io.BytesIO()
    with wave.open(salida, "wb") as archivo:
        archivo.setnchannels(1)
        archivo.setsampwidth(2)
        archivo.setframerate(frecuencia)
        archivo.writeframes(
            b"".join(
                struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / frecuencia)))
                for i in range(int(segundos * frecuencia))
            )
        )
    return salida.getvalue()


def ogg_opus(segundos: float) -> bytes:
    salida = io.BytesIO()
    contenedor = av.open(salida, "w", format="ogg")
    flujo = contenedor.add_stream("libopus", rate=48_000, layout="mono")
    t = np.arange(int(48_000 * segundos)) / 48_000
    muestras = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    for i in range(0, len(muestras), 960):
        cuadro = av.AudioFrame.from_ndarray(
            muestras[i : i + 960].reshape(1, -1), format="flt", layout="mono"
        )
        cuadro.sample_rate = 48_000
        for paquete in flujo.encode(cuadro):
            contenedor.mux(paquete)
    for paquete in flujo.encode(None):
        contenedor.mux(paquete)
    contenedor.close()
    return salida.getvalue()
