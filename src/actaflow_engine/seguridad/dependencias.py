"""Dependencia de FastAPI que exige una firma HMAC valida del backend."""

from __future__ import annotations

import logging

from fastapi import Request

from actaflow_engine.errores import MotorError
from actaflow_engine.seguridad.hmac_firma import (
    CABECERA_FIRMA,
    CABECERA_TIMESTAMP,
    FirmaInvalidaError,
    VerificadorFirma,
)

log = logging.getLogger("actaflow_engine.seguridad")


def ruta_canonica(request: Request) -> str:
    consulta = request.url.query
    return f"{request.url.path}?{consulta}" if consulta else request.url.path


async def exigir_firma(request: Request) -> None:
    verificador: VerificadorFirma = request.app.state.verificador
    cuerpo = await request.body()
    try:
        verificador.verificar(
            request.headers.get(CABECERA_TIMESTAMP),
            request.headers.get(CABECERA_FIRMA),
            request.method,
            ruta_canonica(request),
            cuerpo,
        )
    except FirmaInvalidaError as exc:
        # El motivo exacto solo va al log; al cliente no se le dan pistas.
        log.warning(
            "Peticion rechazada por firma: %s %s (%s)",
            request.method,
            request.url.path,
            exc.motivo.value,
        )
        raise MotorError(401, "firma_invalida", "Peticion no autorizada") from exc
