"""Firma HMAC-SHA256 de peticiones entre servicios de ActaFlow.

Mensaje canonico (identico en el BFF, el backend y el motor):

    timestamp \\n METODO \\n ruta[?consulta] \\n sha256_hex(cuerpo)

La firma viaja en hexadecimal en ``X-ActaFlow-Signature`` y el timestamp (segundos Unix)
en ``X-ActaFlow-Timestamp``. Se rechazan firmas fuera de la ventana de tolerancia para
limitar la reutilizacion de peticiones capturadas.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

CABECERA_TIMESTAMP = "X-ActaFlow-Timestamp"
CABECERA_FIRMA = "X-ActaFlow-Signature"


class MotivoRechazo(StrEnum):
    FALTA_CABECERA = "falta_cabecera"
    TIMESTAMP_INVALIDO = "timestamp_invalido"
    FUERA_DE_VENTANA = "fuera_de_ventana"
    FIRMA_INCORRECTA = "firma_incorrecta"


class FirmaInvalidaError(Exception):
    def __init__(self, motivo: MotivoRechazo) -> None:
        super().__init__(motivo.value)
        self.motivo = motivo


def mensaje_canonico(timestamp: str, metodo: str, ruta: str, cuerpo: bytes) -> str:
    resumen = hashlib.sha256(cuerpo).hexdigest()
    return f"{timestamp}\n{metodo.upper()}\n{ruta}\n{resumen}"


def firmar(secreto: str, timestamp: str, metodo: str, ruta: str, cuerpo: bytes) -> str:
    mensaje = mensaje_canonico(timestamp, metodo, ruta, cuerpo)
    return hmac.new(secreto.encode("utf-8"), mensaje.encode("utf-8"), hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class VerificadorFirma:
    secreto: str
    tolerancia_segundos: int = 300
    reloj: Callable[[], float] = time.time

    def verificar(
        self,
        timestamp: str | None,
        firma: str | None,
        metodo: str,
        ruta: str,
        cuerpo: bytes,
    ) -> None:
        if not timestamp or not firma:
            raise FirmaInvalidaError(MotivoRechazo.FALTA_CABECERA)
        if not timestamp.isdigit() or len(timestamp) > 12:
            raise FirmaInvalidaError(MotivoRechazo.TIMESTAMP_INVALIDO)
        if abs(self.reloj() - int(timestamp)) > self.tolerancia_segundos:
            raise FirmaInvalidaError(MotivoRechazo.FUERA_DE_VENTANA)
        esperada = firmar(self.secreto, timestamp, metodo, ruta, cuerpo)
        if not hmac.compare_digest(esperada, firma.strip().lower()):
            raise FirmaInvalidaError(MotivoRechazo.FIRMA_INCORRECTA)


def cabeceras_firmadas(
    secreto: str, metodo: str, ruta: str, cuerpo: bytes, ahora: float | None = None
) -> dict[str, str]:
    """Construye las cabeceras de firma; util para scripts y tests."""
    timestamp = str(int(time.time() if ahora is None else ahora))
    return {
        CABECERA_TIMESTAMP: timestamp,
        CABECERA_FIRMA: firmar(secreto, timestamp, metodo, ruta, cuerpo),
    }
