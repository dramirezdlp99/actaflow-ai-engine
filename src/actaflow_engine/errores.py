"""Errores uniformes del motor: siempre {"estado", "codigo", "mensaje"}."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("actaflow_engine")

_CODIGOS_HTTP = {
    400: "solicitud_invalida",
    401: "no_autenticado",
    404: "no_encontrado",
    405: "metodo_no_permitido",
    409: "conflicto",
    413: "cuerpo_demasiado_grande",
    422: "solicitud_invalida",
}


class MotorError(Exception):
    def __init__(self, estado: int, codigo: str, mensaje: str) -> None:
        super().__init__(mensaje)
        self.estado = estado
        self.codigo = codigo
        self.mensaje = mensaje


def respuesta_error(estado: int, codigo: str, mensaje: str) -> JSONResponse:
    return JSONResponse(
        status_code=estado,
        content={"estado": estado, "codigo": codigo, "mensaje": mensaje},
    )


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(MotorError)
    async def _error_motor(_: Request, exc: MotorError) -> JSONResponse:
        return respuesta_error(exc.estado, exc.codigo, exc.mensaje)

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        campos = sorted({".".join(str(p) for p in e.get("loc", ())[1:]) for e in exc.errors()})
        detalle = ", ".join(c for c in campos if c) or "cuerpo"
        return respuesta_error(422, "solicitud_invalida", f"Campos invalidos: {detalle}")

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        codigo = _CODIGOS_HTTP.get(exc.status_code, "error_http")
        mensaje = exc.detail if isinstance(exc.detail, str) else codigo
        return respuesta_error(exc.status_code, codigo, mensaje)

    @app.exception_handler(Exception)
    async def _inesperado(_: Request, exc: Exception) -> JSONResponse:
        log.exception("Error inesperado", exc_info=exc)
        return respuesta_error(500, "error_interno", "Error interno del motor")
