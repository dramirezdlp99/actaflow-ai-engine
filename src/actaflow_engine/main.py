"""Aplicacion del motor.

Arranque: uvicorn --factory actaflow_engine.main:create_app --port 8002

El mismo proceso atiende:
  - el servidor gRPC nativo (HTTP/2) en ACTAFLOW_ENGINE_GRPC_BIND (por defecto 127.0.0.1:8102);
  - en el puerto web: GET /health (chequeo de Render) y la pasarela gRPC-Web, que reenvia
    cada llamada al servidor gRPC nativo.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from actaflow_engine import __version__
from actaflow_engine.api import health
from actaflow_engine.config import Settings
from actaflow_engine.diagnostico.benchmark import Ejecutor, ejecutor_subproceso
from actaflow_engine.errores import registrar_manejadores
from actaflow_engine.middleware import CabecerasSeguridad, LimiteCuerpo
from actaflow_engine.rpc.pasarela import PasarelaGrpcWeb
from actaflow_engine.rpc.servidor import crear_servidor

log = logging.getLogger("actaflow_engine")


def destino_local(bind: str, puerto: int) -> str:
    """Direccion para que la pasarela llegue al servidor gRPC del mismo contenedor."""
    host = bind.rsplit(":", 1)[0]
    if host in ("0.0.0.0", "[::]", "::", ""):  # noqa: S104 - solo se compara, no se escucha
        host = "127.0.0.1"
    return f"{host}:{puerto}"


def create_app(
    settings: Settings | None = None,
    ejecutor_benchmark: Ejecutor = ejecutor_subproceso,
) -> FastAPI:
    settings = settings or Settings()  # type: ignore[call-arg]
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
        servidor, puerto = crear_servidor(settings, ejecutor_benchmark)
        await servidor.start()
        pasarela = PasarelaGrpcWeb(
            destino_local(settings.grpc_bind, puerto), settings.max_body_bytes
        )
        await pasarela.iniciar()
        app.state.puerto_grpc = puerto
        app.state.pasarela = pasarela
        log.info("gRPC nativo en el puerto %s; gRPC-Web en el puerto web", puerto)
        try:
            yield
        finally:
            await pasarela.cerrar()
            await servidor.stop(grace=5)

    app = FastAPI(
        title="ActaFlow - Motor de IA",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=ciclo_de_vida,
    )
    app.state.settings = settings

    async def grpc_web(request):  # type: ignore[no-untyped-def]
        return await request.app.state.pasarela.atender(request)

    registrar_manejadores(app)
    app.include_router(health.router)
    # Una llamada gRPC-Web siempre tiene la forma /<paquete.Servicio>/<Metodo>.
    app.add_route("/{servicio}/{metodo}", grpc_web, methods=["POST"])

    # El ultimo middleware agregado es el mas externo.
    app.add_middleware(CabecerasSeguridad, csp_estricta=settings.es_produccion)
    app.add_middleware(LimiteCuerpo, maximo=settings.max_body_bytes)
    return app
