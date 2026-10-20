"""Configuracion del motor, 100 % por variables de entorno (prefijo ACTAFLOW_ENGINE_)."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MODELOS_ASR_SOPORTADOS: tuple[str, ...] = ("tiny", "base", "small")


class Entorno(StrEnum):
    LOCAL = "local"
    PRODUCCION = "produccion"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ACTAFLOW_ENGINE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    hmac_secret: SecretStr = Field(
        ..., description="Secreto HMAC compartido con legal-case-service"
    )
    hmac_tolerance_seconds: int = Field(300, ge=30, le=900)
    environment: Entorno = Entorno.LOCAL
    asr_model: str = "tiny"
    models_dir: Path = Path("./models")
    benchmark_audio: Path = Path("./muestras_generadas/muestra_es.wav")
    benchmark_timeout_seconds: int = Field(600, ge=10, le=3600)
    max_body_bytes: int = Field(5 * 1024 * 1024, ge=1024, le=20 * 1024 * 1024)
    # Servidor gRPC nativo (HTTP/2). En Render solo es alcanzable desde el mismo contenedor:
    # la pasarela gRPC-Web del puerto web le reenvia las llamadas.
    grpc_bind: str = Field("127.0.0.1:8102", pattern=r"^[0-9a-zA-Z.\[\]:]+:[0-9]{1,5}$")
    # Clave privada ECDH P-256 del motor (PKCS#8 en base64url) para abrir lo que se le sella.
    # En local puede faltar (se usa una temporal); en produccion es obligatoria.
    processor_private_key: SecretStr | None = None

    @field_validator("hmac_secret")
    @classmethod
    def _secreto_suficiente(cls, valor: SecretStr) -> SecretStr:
        if len(valor.get_secret_value()) < 32:
            raise ValueError("ACTAFLOW_ENGINE_HMAC_SECRET debe tener al menos 32 caracteres")
        return valor

    @field_validator("asr_model")
    @classmethod
    def _modelo_soportado(cls, valor: str) -> str:
        if valor not in MODELOS_ASR_SOPORTADOS:
            raise ValueError(f"Modelo ASR no soportado: {valor}. Usa {MODELOS_ASR_SOPORTADOS}")
        return valor

    @model_validator(mode="after")
    def _clave_en_produccion(self) -> Settings:
        if self.environment is Entorno.PRODUCCION and self.processor_private_key is None:
            raise ValueError("ACTAFLOW_ENGINE_PROCESSOR_PRIVATE_KEY es obligatoria en produccion")
        return self

    @property
    def es_produccion(self) -> bool:
        return self.environment is Entorno.PRODUCCION
