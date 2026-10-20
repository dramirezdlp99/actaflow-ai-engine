from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
import uvicorn
from fastapi.testclient import TestClient

from actaflow_engine.config import Settings
from actaflow_engine.main import create_app

# Secreto falso y publico, solo para pruebas. Los vectores de firma de los tres repos
# (BFF, microservicios Java y motor) se calcularon con este mismo valor.
SECRETO_PRUEBA = "secreto-de-prueba-publico-solo-para-tests-0123456789"


def crear_modelo_falso(models_dir: Path, nombre: str) -> None:
    carpeta = models_dir / f"faster-whisper-{nombre}"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "model.bin").write_bytes(b"falso")


@pytest.fixture
def models_dir(tmp_path: Path) -> Path:
    carpeta = tmp_path / "models"
    carpeta.mkdir()
    return carpeta


@pytest.fixture
def audio_prueba(tmp_path: Path) -> Path:
    ruta = tmp_path / "muestra_es.wav"
    ruta.write_bytes(b"RIFF-falso")
    return ruta


@pytest.fixture
def settings(models_dir: Path, audio_prueba: Path) -> Settings:
    return Settings(
        hmac_secret=SECRETO_PRUEBA,
        models_dir=models_dir,
        benchmark_audio=audio_prueba,
        max_body_bytes=4096,
        grpc_bind="127.0.0.1:0",
        _env_file=None,
    )


class EjecutorFalso:
    """Simula el subproceso de medicion sin cargar ningun modelo real."""

    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.comandos: list[list[str]] = []

    def __call__(self, comando: list[str], timeout_s: int) -> EjecutorFalso:
        self.comandos.append(comando)
        return self


@pytest.fixture
def ejecutor_ok() -> EjecutorFalso:
    salida = (
        '{"carga_s": 1.2, "transcripcion_s": 30.0, "duracion_audio_s": 30.0, '
        '"factor_tiempo_real": 1.0, "rss_pico_bytes": 250000000, '
        '"texto": "En la ciudad de Pasto se da inicio a la audiencia"}'
    )
    return EjecutorFalso(stdout=salida)


@pytest.fixture
def cliente(settings: Settings, ejecutor_ok: EjecutorFalso) -> Iterator[TestClient]:
    with TestClient(create_app(settings, ejecutor_benchmark=ejecutor_ok)) as cliente:
        yield cliente


@dataclass(frozen=True)
class MotorEnMarcha:
    url_web: str
    destino_grpc: str


@pytest.fixture
def motor(settings: Settings, ejecutor_ok: EjecutorFalso) -> Iterator[MotorEnMarcha]:
    """Motor real: uvicorn (HTTP/1.1, gRPC-Web) + servidor gRPC nativo (HTTP/2), en un hilo."""
    yield from arrancar(create_app(settings, ejecutor_benchmark=ejecutor_ok))


def arrancar(app) -> Iterator[MotorEnMarcha]:  # noqa: ANN001
    """Arranca una app del motor en un hilo y la detiene al final."""
    configuracion = uvicorn.Config(
        app, host="127.0.0.1", port=0, log_level="warning", lifespan="on"
    )
    servidor = uvicorn.Server(configuracion)
    hilo = threading.Thread(target=lambda: asyncio.run(servidor.serve()), daemon=True)
    hilo.start()
    limite = time.monotonic() + 20
    while not servidor.started:
        if time.monotonic() > limite or not hilo.is_alive():
            raise RuntimeError("El motor no arranco")
        time.sleep(0.02)
    puerto_web = servidor.servers[0].sockets[0].getsockname()[1]
    try:
        yield MotorEnMarcha(f"http://127.0.0.1:{puerto_web}", f"127.0.0.1:{app.state.puerto_grpc}")
    finally:
        servidor.should_exit = True
        hilo.join(timeout=15)
