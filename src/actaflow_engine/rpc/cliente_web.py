"""Cliente gRPC-Web minimo (sin dependencias), para scripts de diagnostico y tests.

Firma cada llamada con HMAC y decodifica las tramas de respuesta. En produccion quien llama
al motor es legal-case-service (Java); este cliente sirve para medirlo desde un computador.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass

from google.protobuf.message import Message

from actaflow_engine.rpc import tramas
from actaflow_engine.seguridad.hmac_firma import metadatos_firmados

MAX_RESPUESTA = 16 * 1024 * 1024


@dataclass
class GrpcWebError(Exception):
    codigo: int
    mensaje: str
    trailers: dict[str, str]

    def __str__(self) -> str:
        return f"gRPC {self.codigo}: {self.mensaje}"


def llamar[M: Message](
    url_base: str,
    metodo_grpc: str,
    peticion: Message,
    tipo_respuesta: type[M],
    secreto: str,
    timeout_s: float = 120.0,
) -> M:
    """Llamada unaria gRPC-Web firmada. Lanza GrpcWebError si el estado no es OK."""
    if not url_base.startswith(("http://", "https://")):
        raise ValueError("La URL del motor debe empezar por http:// o https://")
    cuerpo = peticion.SerializeToString()
    cabeceras = {
        "Content-Type": "application/grpc-web+proto",
        "X-Grpc-Web": "1",
        "grpc-timeout": f"{int(timeout_s)}S",
    }
    cabeceras.update(dict(metadatos_firmados(secreto, metodo_grpc, cuerpo)))
    solicitud = urllib.request.Request(  # noqa: S310 - esquema comprobado arriba
        f"{url_base.rstrip('/')}{metodo_grpc}",
        data=tramas.trama_datos(cuerpo),
        headers=cabeceras,
        method="POST",
    )
    try:
        with urllib.request.urlopen(solicitud, timeout=timeout_s + 10) as respuesta:  # noqa: S310
            datos = respuesta.read(MAX_RESPUESTA + 1)
    except urllib.error.HTTPError as exc:
        raise GrpcWebError(14, f"HTTP {exc.code}", {}) from exc

    mensajes: list[bytes] = []
    trailers: dict[str, str] = {}
    for trama in tramas.decodificar(datos, MAX_RESPUESTA):
        if trama.es_trailers:
            trailers = tramas.leer_trailers(trama.contenido)
        else:
            mensajes.append(trama.contenido)
    codigo = int(trailers.get("grpc-status", "2"))
    if codigo != 0:
        raise GrpcWebError(codigo, trailers.get("grpc-message", ""), trailers)
    resultado = tipo_respuesta()
    if mensajes:
        resultado.ParseFromString(mensajes[0])
    return resultado
