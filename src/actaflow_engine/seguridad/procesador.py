"""Patron "procesador sellado": el motor abre en memoria lo que el navegador sella para el.

El navegador genera una clave de contenido K, cifra la carga con K (AES-256-GCM) y envuelve K para
la clave publica del motor con el MISMO esquema con que se envuelven las claves de los casos:

    ECDH P-256 (efimera del navegador x clave del motor) -> HKDF-SHA-256
        (salt = clave publica efimera,
         info = "actaflow/clave-de-caso/v1|" + id de la clave del motor)
    -> AES-256-GCM sobre K, con AAD = id de la clave del motor.

El motor desenvuelve K, descifra la carga, la procesa y cifra el resultado con la misma K. Nada
toca el disco y K se descarta al terminar. AAD de la carga y del resultado (nunca se transmite):
"actaflow/v1|<proposito>|<case_id>|<resource_id>".
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from actaflow.crypto.v1 import crypto_pb2

INFO_ENVOLTURA = b"actaflow/clave-de-caso/v1|"
ALGORITMO = "ECDH-P256"

log = logging.getLogger("actaflow_engine.seguridad")


class SobreInvalidoError(Exception):
    """No se pudo abrir el sobre: clave equivocada, datos alterados o contexto distinto."""


def aad(proposito: str, caso_id: str, recurso_id: str) -> bytes:
    return f"actaflow/v1|{proposito}|{caso_id}|{recurso_id}".encode()


@dataclass(frozen=True)
class ClaveProcesador:
    privada: ec.EllipticCurvePrivateKey

    @classmethod
    def desde_pkcs8(cls, texto_base64: str) -> ClaveProcesador:
        """Clave privada PKCS#8 (DER) en base64 o base64url, como en la variable de entorno."""
        relleno = "=" * (-len(texto_base64.strip()) % 4)
        der = base64.urlsafe_b64decode(
            texto_base64.strip().replace("+", "-").replace("/", "_") + relleno
        )
        privada = serialization.load_der_private_key(der, password=None)
        if not isinstance(privada, ec.EllipticCurvePrivateKey) or privada.curve.name != "secp256r1":
            raise ValueError("La clave del procesador debe ser ECDH P-256")
        return cls(privada)

    @classmethod
    def nueva(cls) -> ClaveProcesador:
        return cls(ec.generate_private_key(ec.SECP256R1()))

    def pkcs8_base64url(self) -> str:
        der = self.privada.private_bytes(
            serialization.Encoding.DER,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        return base64.urlsafe_b64encode(der).decode().rstrip("=")

    @property
    def publica(self) -> bytes:
        """Punto P-256 sin comprimir (65 bytes), el formato que importa WebCrypto ("raw")."""
        return self.privada.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )

    @property
    def huella(self) -> str:
        return hashlib.sha256(self.publica).hexdigest()

    @property
    def id_clave(self) -> str:
        return f"motor:{self.huella[:16]}"

    def clave_publica(self) -> crypto_pb2.PublicKey:
        return crypto_pb2.PublicKey(
            key_id=self.id_clave,
            algorithm=ALGORITMO,
            public_key=self.publica,
            fingerprint_sha256=self.huella,
        )

    # ------------------------------------------------------------------ envolturas

    def desenvolver(self, envoltura: crypto_pb2.WrappedKey) -> bytes:
        if envoltura.recipient_key_id != self.id_clave:
            raise SobreInvalidoError("La clave de contenido no esta envuelta para este motor")
        try:
            efimera = ec.EllipticCurvePublicKey.from_encoded_point(
                ec.SECP256R1(), envoltura.ephemeral_public_key
            )
            compartido = self.privada.exchange(ec.ECDH(), efimera)
            kek = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=envoltura.ephemeral_public_key,
                info=INFO_ENVOLTURA + envoltura.recipient_key_id.encode(),
            ).derive(compartido)
            clave = AESGCM(kek).decrypt(
                envoltura.nonce, envoltura.wrapped_key, envoltura.recipient_key_id.encode()
            )
        except (InvalidTag, ValueError) as error:
            raise SobreInvalidoError("No se pudo desenvolver la clave de contenido") from error
        if len(clave) != 32:
            raise SobreInvalidoError("La clave de contenido no es AES-256")
        return clave


def envolver(
    clave: bytes, id_destinatario: str, publica_destinatario: bytes
) -> crypto_pb2.WrappedKey:
    """Lo que hace el navegador (`envolverClave`); sirve en pruebas y en el trabajador."""
    destinatario = ec.EllipticCurvePublicKey.from_encoded_point(
        ec.SECP256R1(), publica_destinatario
    )
    efimera = ec.generate_private_key(ec.SECP256R1())
    efimera_cruda = efimera.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    kek = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=efimera_cruda,
        info=INFO_ENVOLTURA + id_destinatario.encode(),
    ).derive(efimera.exchange(ec.ECDH(), destinatario))
    nonce = os.urandom(12)
    return crypto_pb2.WrappedKey(
        suite=crypto_pb2.CIPHER_SUITE_ECDH_P256_HKDF_SHA256_AES_256_GCM,
        recipient_key_id=id_destinatario,
        ephemeral_public_key=efimera_cruda,
        nonce=nonce,
        wrapped_key=AESGCM(kek).encrypt(nonce, clave, id_destinatario.encode()),
    )


def cifrar(
    clave: bytes, id_clave: str, datos: bytes, tipo: str, contexto: bytes
) -> crypto_pb2.EncryptedBlob:
    nonce = os.urandom(12)
    return crypto_pb2.EncryptedBlob(
        suite=crypto_pb2.CIPHER_SUITE_AES_256_GCM,
        key_id=id_clave,
        nonce=nonce,
        ciphertext=AESGCM(clave).encrypt(nonce, datos, contexto),
        plaintext_type=tipo,
    )


def descifrar(clave: bytes, blob: crypto_pb2.EncryptedBlob, tipo: str, contexto: bytes) -> bytes:
    if blob.plaintext_type != tipo:
        raise SobreInvalidoError(f"Se esperaba {tipo} y llego {blob.plaintext_type or 'sin tipo'}")
    try:
        return AESGCM(clave).decrypt(blob.nonce, blob.ciphertext, contexto)
    except InvalidTag as error:
        raise SobreInvalidoError(
            "La carga no se pudo descifrar (clave o contexto distintos)"
        ) from error


@dataclass(frozen=True)
class Abierto:
    """Contenido de un sobre abierto: la carga en claro y la clave para cifrar el resultado."""

    datos: bytes
    clave: bytes
    id_clave: str


def abrir(
    procesador: ClaveProcesador, sobre: crypto_pb2.SealedEnvelope, tipo: str, contexto: bytes
) -> Abierto:
    clave = procesador.desenvolver(sobre.processor_key)
    return Abierto(descifrar(clave, sobre.payload, tipo, contexto), clave, sobre.payload.key_id)


def clave_desde_entorno(texto: str | None, produccion: bool) -> ClaveProcesador:
    """Clave del motor: de la variable de entorno; en local, una temporal si no hay."""
    if texto:
        return ClaveProcesador.desde_pkcs8(texto)
    if produccion:
        raise RuntimeError("Falta ACTAFLOW_ENGINE_PROCESSOR_PRIVATE_KEY en produccion")
    log.warning(
        "Sin ACTAFLOW_ENGINE_PROCESSOR_PRIVATE_KEY: clave temporal (cambia en cada arranque)"
    )
    return ClaveProcesador.nueva()
