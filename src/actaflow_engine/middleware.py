"""Middlewares ASGI: cabeceras de seguridad y limite de tamano del cuerpo."""

from __future__ import annotations

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

CABECERAS_SEGURIDAD: tuple[tuple[bytes, bytes], ...] = (
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"cache-control", b"no-store"),
    (b"cross-origin-resource-policy", b"same-origin"),
)
CSP_ESTRICTA = (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'")


class CabecerasSeguridad:
    def __init__(self, app: ASGIApp, csp_estricta: bool) -> None:
        self.app = app
        self.cabeceras = CABECERAS_SEGURIDAD + ((CSP_ESTRICTA,) if csp_estricta else ())

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def enviar(mensaje: Message) -> None:
            if mensaje["type"] == "http.response.start":
                existentes = [
                    (k, v) for k, v in mensaje.get("headers", []) if k.lower() != b"server"
                ]
                mensaje["headers"] = existentes + list(self.cabeceras)
            await send(mensaje)

        await self.app(scope, receive, enviar)


class _CuerpoDemasiadoGrandeError(Exception):
    pass


class LimiteCuerpo:
    """Rechaza con 413 los cuerpos mayores que ``maximo`` bytes, declarados o reales."""

    def __init__(self, app: ASGIApp, maximo: int) -> None:
        self.app = app
        self.maximo = maximo

    async def _responder_413(self, send: Send) -> None:
        cuerpo = json.dumps(
            {
                "estado": 413,
                "codigo": "cuerpo_demasiado_grande",
                "mensaje": f"El cuerpo supera {self.maximo} bytes",
            }
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(cuerpo)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": cuerpo})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        for nombre, valor in scope.get("headers", []):
            if nombre == b"content-length" and valor.isdigit() and int(valor) > self.maximo:
                await self._responder_413(send)
                return

        recibidos = 0
        respuesta_iniciada = False

        async def recibir() -> Message:
            nonlocal recibidos
            mensaje = await receive()
            if mensaje["type"] == "http.request":
                recibidos += len(mensaje.get("body", b""))
                if recibidos > self.maximo:
                    raise _CuerpoDemasiadoGrandeError
            return mensaje

        async def enviar(mensaje: Message) -> None:
            nonlocal respuesta_iniciada
            if mensaje["type"] == "http.response.start":
                respuesta_iniciada = True
            await send(mensaje)

        try:
            await self.app(scope, recibir, enviar)
        except _CuerpoDemasiadoGrandeError:
            if not respuesta_iniciada:
                await self._responder_413(send)
