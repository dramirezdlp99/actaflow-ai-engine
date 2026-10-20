"""Numeros en espanol ("un millon quinientos mil" -> 1500000) y cifras con separadores."""

from __future__ import annotations

import re
import unicodedata

_UNIDADES = {
    "cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12,
    "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16, "diecisiete": 17,
    "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiun": 21, "veintiuno": 21,
    "veintiuna": 21, "veintidos": 22, "veintitres": 23, "veinticuatro": 24, "veinticinco": 25,
    "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29, "treinta": 30,
    "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90,
    "cien": 100, "ciento": 100, "doscientos": 200, "doscientas": 200, "trescientos": 300,
    "trescientas": 300, "cuatrocientos": 400, "cuatrocientas": 400, "quinientos": 500,
    "quinientas": 500, "seiscientos": 600, "seiscientas": 600, "setecientos": 700,
    "setecientas": 700, "ochocientos": 800, "ochocientas": 800, "novecientos": 900,
    "novecientas": 900,
}  # fmt: skip
_ESCALAS = {
    "mil": 1_000,
    "millon": 1_000_000,
    "millones": 1_000_000,
    "billon": 10**12,
    "billones": 10**12,
}

PALABRAS_NUMERO = sorted({*_UNIDADES, *_ESCALAS}, key=len, reverse=True)
_ALTERNATIVA = "|".join(PALABRAS_NUMERO)
# Una secuencia de palabras numericas ("un millon quinientos mil"), sin tildes y en minusculas.
PATRON_PALABRAS = rf"\b(?:{_ALTERNATIVA})\b(?:\s+(?:y\s+)?(?:{_ALTERNATIVA})\b)*"


def sin_tildes(texto: str) -> str:
    """Minusculas y sin tildes, conservando la longitud (para que las posiciones sigan valiendo)."""
    normal = []
    for caracter in texto:
        base = unicodedata.normalize("NFD", caracter)[0]
        normal.append(base.lower() if len(base.lower()) == 1 else caracter.lower())
    return "".join(normal)


def palabras_a_numero(texto: str) -> int | None:
    """Convierte "un millon quinientos mil" en 1500000. None si no es un numero en palabras."""
    palabras = [p for p in re.split(r"\s+", sin_tildes(texto).strip()) if p and p != "y"]
    if not palabras:
        return None
    total = 0
    acumulado = 0  # lo que va por debajo del millon
    grupo = 0  # lo que va por debajo de mil
    for palabra in palabras:
        if palabra in _UNIDADES:
            grupo += _UNIDADES[palabra]
        elif palabra == "mil":
            acumulado += (grupo or 1) * 1_000
            grupo = 0
        elif palabra in _ESCALAS:
            total += (acumulado + grupo or 1) * _ESCALAS[palabra]
            acumulado = 0
            grupo = 0
        else:
            return None
    return total + acumulado + grupo


def cifra_a_numero(texto: str) -> tuple[int, int] | None:
    """Cifra con separadores colombianos: "1.500.000", "1'500.000", "1 500 000,50" -> (1500000, 50).

    Devuelve (unidades, centavos).
    """
    limpio = texto.strip().replace("’", "'")
    centavos = 0
    coincidencia = re.fullmatch(r"(\d{1,3}(?:[.' ]\d{3})+|\d+)(?:,(\d{1,2}))?", limpio)
    if not coincidencia:
        return None
    unidades = int(re.sub(r"[.' ]", "", coincidencia.group(1)))
    if coincidencia.group(2):
        centavos = int(coincidencia.group(2).ljust(2, "0"))
    return unidades, centavos
