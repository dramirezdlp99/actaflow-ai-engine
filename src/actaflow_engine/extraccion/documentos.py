"""Documentos de identidad colombianos y el digito de verificacion del NIT (DIAN, modulo 11)."""

from __future__ import annotations

_PESOS_NIT = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)


def digito_verificacion_nit(numero: str) -> int:
    """Digito de verificacion de un NIT (base sin el digito), algoritmo de la DIAN."""
    digitos = [int(c) for c in reversed(numero)]
    if not digitos or len(digitos) > len(_PESOS_NIT):
        raise ValueError("NIT no valido")
    residuo = sum(d * p for d, p in zip(digitos, _PESOS_NIT, strict=False)) % 11
    return residuo if residuo in (0, 1) else 11 - residuo


def solo_digitos(texto: str) -> str:
    return "".join(c for c in texto if c.isdigit())
