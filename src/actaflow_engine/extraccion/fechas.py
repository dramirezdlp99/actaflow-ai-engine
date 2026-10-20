"""Fechas: festivos de Colombia, dias habiles y fechas escritas en texto."""

from __future__ import annotations

import re
from datetime import date, timedelta
from functools import lru_cache

from actaflow_engine.extraccion.numeros import PATRON_PALABRAS, palabras_a_numero

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}  # fmt: skip
_MES = "|".join(MESES)
_DIA = rf"(?:\d{{1,2}}|primero|{PATRON_PALABRAS})"
_ANIO = rf"(?:\d{{4}}|{PATRON_PALABRAS})"
# "15 de noviembre de 2026", "el primero de diciembre", "quince (15) de enero del 2027".
PATRON_FECHA_TEXTO = re.compile(
    rf"\b(?P<dia>{_DIA})(?:\s*\(\d{{1,2}}\))?\s+de\s+(?P<mes>{_MES})"
    rf"(?:\s+(?:de|del)\s+(?P<anio>{_ANIO})(?:\s*\(\d{{4}}\))?)?",
)
PATRON_FECHA_NUMERICA = re.compile(r"\b(?P<dia>\d{1,2})/(?P<mes>\d{1,2})/(?P<anio>\d{4})\b")


def _pascua(anio: int) -> date:
    """Domingo de Pascua (algoritmo anonimo gregoriano)."""
    a = anio % 19
    b, c = divmod(anio, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    mes, dia = divmod(h + m - 7 * n + 114, 31)
    return date(anio, mes, dia + 1)


def _lunes_siguiente(dia: date) -> date:
    return dia + timedelta(days=(7 - dia.weekday()) % 7)


@lru_cache(maxsize=64)
def festivos(anio: int) -> frozenset[date]:
    """Festivos de Colombia (Ley 51 de 1983, "ley Emiliani")."""
    fijos = [
        date(anio, 1, 1),
        date(anio, 5, 1),
        date(anio, 7, 20),
        date(anio, 8, 7),
        date(anio, 12, 8),
        date(anio, 12, 25),
    ]
    trasladables = [
        date(anio, 1, 6),
        date(anio, 3, 19),
        date(anio, 6, 29),
        date(anio, 8, 15),
        date(anio, 10, 12),
        date(anio, 11, 1),
        date(anio, 11, 11),
    ]
    pascua = _pascua(anio)
    semana_santa = [pascua - timedelta(days=3), pascua - timedelta(days=2)]
    de_pascua = [
        pascua + timedelta(days=dias) for dias in (43, 64, 71)
    ]  # Ascension, Corpus, Sagrado Corazon
    return frozenset([*fijos, *map(_lunes_siguiente, trasladables), *semana_santa, *de_pascua])


def es_habil(dia: date) -> bool:
    return dia.weekday() < 5 and dia not in festivos(dia.year)


def sumar_dias(desde: date, dias: int, habiles: bool) -> date:
    """Cuenta `dias` a partir del dia siguiente a `desde` (habiles o calendario)."""
    if not habiles:
        return desde + timedelta(days=dias)
    actual = desde
    contados = 0
    while contados < dias:
        actual += timedelta(days=1)
        if es_habil(actual):
            contados += 1
    return actual


def fecha_en_texto(coincidencia: re.Match[str], referencia: date) -> date | None:
    """Fecha de una coincidencia de PATRON_FECHA_TEXTO (texto sin tildes y en minusculas).

    Sin anio, toma el de la referencia, o el siguiente si la fecha ya habria pasado.
    """
    texto_dia = coincidencia.group("dia")
    dia = (
        1
        if texto_dia == "primero"
        else int(texto_dia)
        if texto_dia.isdigit()
        else palabras_a_numero(texto_dia)
    )
    mes = MESES[coincidencia.group("mes")]
    texto_anio = coincidencia.group("anio")
    if texto_anio:
        anio = int(texto_anio) if texto_anio.isdigit() else palabras_a_numero(texto_anio)
    else:
        anio = referencia.year
    if not dia or not anio:
        return None
    try:
        resultado = date(anio, mes, dia)
    except ValueError:
        return None
    if not texto_anio and resultado < referencia:
        try:
            resultado = date(anio + 1, mes, dia)
        except ValueError:
            return None
    return resultado


def fecha_numerica(coincidencia: re.Match[str]) -> date | None:
    try:
        return date(
            int(coincidencia.group("anio")),
            int(coincidencia.group("mes")),
            int(coincidencia.group("dia")),
        )
    except ValueError:
        return None
