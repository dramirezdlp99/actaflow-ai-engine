"""Configuracion del motor, 100 % por variables de entorno (prefijo ACTAFLOW_ENGINE_)."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
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

    hmac_secret: SecretStr = Field(..., description="Secreto HMAC compartido con el backend")
    hmac_tolerance_seconds: int = Field(300, ge=30, le=900)
    environment: Entorno = Entorno.LOCAL
    asr_model: str = "tiny"
    models_dir: Path = Path("./models")
    benchmark_audio: Path = Path("./muestras_generadas/muestra_es.wav")
    benchmark_timeout_seconds: int = Field(600, ge=10, le=3600)
    max_body_bytes: int = Field(5 * 1024 * 1024, ge=1024, le=20 * 1024 * 1024)

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

    @property
    def es_produccion(self) -> bool:
        return self.environment is Entorno.PRODUCCION
