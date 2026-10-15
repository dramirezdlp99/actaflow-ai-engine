"""Codificacion de tramas gRPC-Web (protocolo binario, application/grpc-web+proto).

Cada trama es: 1 byte de banderas + 4 bytes de longitud (big-endian) + contenido.
  - bandera 0x00: un mensaje protobuf;
  - bandera 0x80: los trailers, como texto "clave:valor\\r\\n" (aqui viaja grpc-status);
  - bandera 0x01: mensaje comprimido (no se admite: ActaFlow no comprime, el contenido
    ya va cifrado y no se comprimiria).

Especificacion: https://github.com/grpc/grpc/blob/master/doc/PROTOCOL-WEB.md
"""

from __future__ import annotations

import base64
import struct
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import quote, unquote

BANDERA_DATOS = 0x00
BANDERA_COMPRIMIDA = 0x01
BANDERA_TRAILERS = 0x80
CABECERA = struct.Struct(">BI")


class TramaInvalidaError(ValueError):
    """El cuerpo no es una secuencia valida de tramas gRPC-Web."""


@dataclass(frozen=True)
class Trama:
    bandera: int
    contenido: bytes

    @property
    def es_trailers(self) -> bool:
        return bool(self.bandera & BANDERA_TRAILERS)


def codificar(bandera: int, contenido: bytes) -> bytes:
    return CABECERA.pack(bandera, len(contenido)) + contenido


def trama_datos(mensaje: bytes) -> bytes:
    return codificar(BANDERA_DATOS, mensaje)


def decodificar(cuerpo: bytes, max_mensaje: int) -> list[Trama]:
    """Separa un cuerpo completo en tramas, comprobando longitudes y banderas."""
    tramas: list[Trama] = []
    posicion = 0
    while posicion < len(cuerpo):
        if len(cuerpo) - posicion < CABECERA.size:
            raise TramaInvalidaError("Cabecera de trama incompleta")
        bandera, longitud = CABECERA.unpack_from(cuerpo, posicion)
        posicion += CABECERA.size
        if longitud > max_mensaje:
            raise TramaInvalidaError(f"Trama de {longitud} bytes supera el maximo {max_mensaje}")
        if len(cuerpo) - posicion < longitud:
            raise TramaInvalidaError("Trama truncada")
        if bandera & BANDERA_COMPRIMIDA:
            raise TramaInvalidaError("Compresion no admitida")
        if bandera not in (BANDERA_DATOS, BANDERA_TRAILERS):
            raise TramaInvalidaError(f"Bandera desconocida 0x{bandera:02x}")
        tramas.append(Trama(bandera, cuerpo[posicion : posicion + longitud]))
        posicion += longitud
    return tramas


def _valor_metadato(clave: str, valor: str | bytes) -> str:
    # Los metadatos binarios (sufijo -bin) viajan en base64, como exige gRPC.
    if clave.endswith("-bin"):
        datos = valor if isinstance(valor, bytes) else valor.encode()
        return base64.b64encode(datos).decode("ascii").rstrip("=")
    return valor.decode() if isinstance(valor, bytes) else valor


def trama_trailers(
    codigo: int, mensaje: str = "", metadatos: Iterable[tuple[str, str | bytes]] = ()
) -> bytes:
    """Trailers finales: grpc-status, grpc-message (codificado en porcentaje) y extras."""
    lineas = [f"grpc-status:{codigo}"]
    if mensaje:
        lineas.append(f"grpc-message:{quote(mensaje, safe=' ')}")
    for clave, valor in metadatos:
        clave = clave.lower()
        if clave in ("grpc-status", "grpc-message"):
            continue
        lineas.append(f"{clave}:{_valor_metadato(clave, valor)}")
    texto = "".join(f"{linea}\r\n" for linea in lineas)
    return codificar(BANDERA_TRAILERS, texto.encode("utf-8"))


def leer_trailers(contenido: bytes) -> dict[str, str]:
    """Interpreta el texto de una trama de trailers (para el cliente gRPC-Web)."""
    resultado: dict[str, str] = {}
    for linea in contenido.decode("utf-8").split("\r\n"):
        if not linea:
            continue
        clave, _, valor = linea.partition(":")
        resultado[clave.strip().lower()] = valor.strip()
    if "grpc-message" in resultado:
        resultado["grpc-message"] = unquote(resultado["grpc-message"])
    return resultado
