"""GET /health: publico. Lo usan Render (chequeo de salud) y el backend (para despertar
el motor antes de enviarle trabajo). No revela secretos ni datos de audiencias."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from actaflow_engine import __version__
from actaflow_engine.config import Settings
from actaflow_engine.inventario import inventario

router = APIRouter(tags=["salud"])


class EstadoAsr(BaseModel):
    configurado: str
    disponibles: list[str]
    listo: bool


class EstadoNlp(BaseModel):
    disponibles: list[str]


class Modelos(BaseModel):
    asr: EstadoAsr
    nlp: EstadoNlp


class RespuestaHealth(BaseModel):
    servicio: Literal["actaflow-ai-engine"] = "actaflow-ai-engine"
    version: str
    estado: Literal["ok", "degradado"]
    entorno: str
    modelos: Modelos


@router.get("/health", response_model=RespuestaHealth)
def health(request: Request) -> RespuestaHealth:
    settings: Settings = request.app.state.settings
    inv = inventario(settings.models_dir, settings.asr_model)
    return RespuestaHealth(
        version=__version__,
        estado="ok" if inv.asr_listo else "degradado",
        entorno=settings.environment.value,
        modelos=Modelos(
            asr=EstadoAsr(
                configurado=inv.asr_configurado,
                disponibles=inv.asr_disponibles,
                listo=inv.asr_listo,
            ),
            nlp=EstadoNlp(disponibles=inv.nlp_disponibles),
        ),
    )
