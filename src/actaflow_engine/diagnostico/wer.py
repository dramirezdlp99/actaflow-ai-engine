"""Tasa de error de palabras (WER) para comparar la transcripcion con el guion leido."""

from __future__ import annotations

import re
import unicodedata

_NO_PALABRA = re.compile(r"[^\w\s]", flags=re.UNICODE)


def normalizar(texto: str) -> list[str]:
    """Minusculas, sin tildes ni puntuacion, y separado en palabras."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn"
    )
    return _NO_PALABRA.sub(" ", sin_tildes).split()


def distancia_edicion(referencia: list[str], hipotesis: list[str]) -> int:
    """Distancia de Levenshtein por palabras, con memoria O(len(hipotesis))."""
    previa = list(range(len(hipotesis) + 1))
    for i, palabra_ref in enumerate(referencia, start=1):
        actual = [i] + [0] * len(hipotesis)
        for j, palabra_hip in enumerate(hipotesis, start=1):
            costo = 0 if palabra_ref == palabra_hip else 1
            actual[j] = min(previa[j] + 1, actual[j - 1] + 1, previa[j - 1] + costo)
        previa = actual
    return previa[-1]


def wer(referencia: str, hipotesis: str) -> float:
    """WER = ediciones / palabras de la referencia. Sin referencia devuelve 0 o 1."""
    ref = normalizar(referencia)
    hip = normalizar(hipotesis)
    if not ref:
        return 0.0 if not hip else 1.0
    return distancia_edicion(ref, hip) / len(ref)
