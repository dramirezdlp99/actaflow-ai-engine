from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from actaflow_engine.config import Settings
from actaflow_engine.main import create_app

# Secreto falso y publico, solo para pruebas. Los vectores de firma de los tres repos
# (BFF, backend y motor) se calcularon con este mismo valor.
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
        max_body_bytes=2048,
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
def cliente(settings: Settings, ejecutor_ok: EjecutorFalso) -> TestClient:
    return TestClient(create_app(settings, ejecutor_benchmark=ejecutor_ok))
