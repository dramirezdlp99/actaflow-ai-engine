"""Fabrica de la aplicacion FastAPI del motor.

Arranque: uvicorn --factory actaflow_engine.main:create_app --port 8002
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from actaflow_engine import __version__
from actaflow_engine.api import diagnostico, health
from actaflow_engine.config import Settings
from actaflow_engine.diagnostico.benchmark import Ejecutor, ejecutor_subproceso
from actaflow_engine.errores import registrar_manejadores
from actaflow_engine.middleware import CabecerasSeguridad, LimiteCuerpo
from actaflow_engine.seguridad.hmac_firma import VerificadorFirma


def create_app(
    settings: Settings | None = None,
    ejecutor_benchmark: Ejecutor = ejecutor_subproceso,
) -> FastAPI:
    settings = settings or Settings()  # type: ignore[call-arg]
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    app = FastAPI(
        title="ActaFlow - Motor de IA",
        version=__version__,
        docs_url=None if settings.es_produccion else "/docs",
        redoc_url=None,
        openapi_url=None if settings.es_produccion else "/openapi.json",
    )
    app.state.settings = settings
    app.state.verificador = VerificadorFirma(
        secreto=settings.hmac_secret.get_secret_value(),
        tolerancia_segundos=settings.hmac_tolerance_seconds,
    )
    app.state.ejecutor_benchmark = ejecutor_benchmark

    registrar_manejadores(app)
    app.include_router(health.router)
    app.include_router(diagnostico.router)

    # El ultimo middleware agregado es el mas externo.
    app.add_middleware(CabecerasSeguridad, csp_estricta=settings.es_produccion)
    app.add_middleware(LimiteCuerpo, maximo=settings.max_body_bytes)
    return app
