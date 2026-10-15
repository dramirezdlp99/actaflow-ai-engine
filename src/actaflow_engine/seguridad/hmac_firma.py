"""Firma HMAC-SHA256 de las llamadas gRPC entre servicios de ActaFlow.

Mensaje canonico (identico en el BFF, los microservicios Java y el motor):

    timestamp \\n RPC \\n /<paquete.Servicio>/<Metodo> \\n sha256_hex(bytes protobuf de la peticion)

Viaja en los metadatos gRPC ``x-actaflow-timestamp`` (segundos Unix) y
``x-actaflow-signature`` (hex). Al firmar los bytes exactos del mensaje, un intermediario no
puede alterarlo sin invalidar la firma. En los RPC con streaming del cliente se firma el hash
de un mensaje vacio (cada trozo ya va protegido por AES-GCM).
"""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

METADATO_TIMESTAMP = "x-actaflow-timestamp"
METADATO_FIRMA = "x-actaflow-signature"
SIN_CUERPO = b""


class MotivoRechazo(StrEnum):
    FALTA_METADATO = "falta_metadato"
    TIMESTAMP_INVALIDO = "timestamp_invalido"
    FUERA_DE_VENTANA = "fuera_de_ventana"
    FIRMA_INCORRECTA = "firma_incorrecta"


class FirmaInvalidaError(Exception):
    def __init__(self, motivo: MotivoRechazo) -> None:
        super().__init__(motivo.value)
        self.motivo = motivo


def mensaje_canonico(timestamp: str, metodo_grpc: str, cuerpo: bytes) -> str:
    resumen = hashlib.sha256(cuerpo).hexdigest()
    return f"{timestamp}\nRPC\n{metodo_grpc}\n{resumen}"


def firmar(secreto: str, timestamp: str, metodo_grpc: str, cuerpo: bytes) -> str:
    mensaje = mensaje_canonico(timestamp, metodo_grpc, cuerpo)
    return hmac.new(secreto.encode("utf-8"), mensaje.encode("utf-8"), hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class VerificadorFirma:
    secreto: str
    tolerancia_segundos: int = 300
    reloj: Callable[[], float] = time.time

    def verificar(
        self, timestamp: str | None, firma: str | None, metodo_grpc: str, cuerpo: bytes
    ) -> None:
        if not timestamp or not firma:
            raise FirmaInvalidaError(MotivoRechazo.FALTA_METADATO)
        if not timestamp.isdigit() or len(timestamp) > 12:
            raise FirmaInvalidaError(MotivoRechazo.TIMESTAMP_INVALIDO)
        if abs(self.reloj() - int(timestamp)) > self.tolerancia_segundos:
            raise FirmaInvalidaError(MotivoRechazo.FUERA_DE_VENTANA)
        esperada = firmar(self.secreto, timestamp, metodo_grpc, cuerpo)
        if not hmac.compare_digest(esperada, firma.strip().lower()):
            raise FirmaInvalidaError(MotivoRechazo.FIRMA_INCORRECTA)


def metadatos_firmados(
    secreto: str, metodo_grpc: str, cuerpo: bytes, ahora: float | None = None
) -> list[tuple[str, str]]:
    """Metadatos gRPC listos para una llamada saliente; util en scripts y tests."""
    timestamp = str(int(time.time() if ahora is None else ahora))
    return [
        (METADATO_TIMESTAMP, timestamp),
        (METADATO_FIRMA, firmar(secreto, timestamp, metodo_grpc, cuerpo)),
    ]
