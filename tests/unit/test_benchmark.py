from __future__ import annotations

import subprocess
from pathlib import Path

from actaflow_engine.diagnostico.benchmark import (
    EstadoMedicion,
    construir_comando,
    ejecutar_benchmark,
)
from actaflow_engine.diagnostico.entorno import EntornoContenedor
from tests.conftest import EjecutorFalso, crear_modelo_falso

ENTORNO = EntornoContenedor(memoria_limite_bytes=536870912, cpu_cuota_nucleos=0.1, cpus_visibles=2)


def _correr(models_dir: Path, audio: Path, ejecutor, modelos=("tiny",), referencia=None):
    return ejecutar_benchmark(
        list(modelos),
        models_dir,
        audio,
        referencia,
        60,
        ejecutor=ejecutor,
        lector_entorno=lambda: ENTORNO,
    )


def test_medicion_correcta_calcula_wer_contra_la_referencia(models_dir, audio_prueba, ejecutor_ok):
    crear_modelo_falso(models_dir, "tiny")
    informe = _correr(
        models_dir,
        audio_prueba,
        ejecutor_ok,
        referencia="En la ciudad de Pasto se da inicio a la audiencia",
    )
    resultado = informe.resultados[0]
    assert resultado.estado is EstadoMedicion.OK
    assert resultado.metricas["factor_tiempo_real"] == 1.0
    assert resultado.wer == 0.0


def test_modelo_no_instalado_no_lanza_subproceso(models_dir, audio_prueba, ejecutor_ok):
    resultado = _correr(models_dir, audio_prueba, ejecutor_ok, ("small",)).resultados[0]
    assert resultado.estado is EstadoMedicion.NO_INSTALADO
    assert ejecutor_ok.comandos == []


def test_proceso_muerto_por_sigkill_se_informa_como_oom(models_dir, audio_prueba):
    crear_modelo_falso(models_dir, "small")
    for codigo in (-9, 137):
        resultado = _correr(
            models_dir, audio_prueba, EjecutorFalso(returncode=codigo), ("small",)
        ).resultados[0]
        assert resultado.estado is EstadoMedicion.OOM


def test_timeout_se_informa_sin_romper_el_resto(models_dir, audio_prueba, ejecutor_ok):
    crear_modelo_falso(models_dir, "tiny")
    crear_modelo_falso(models_dir, "base")

    def ejecutor(comando, timeout_s):
        if "faster-whisper-tiny" in " ".join(comando):
            raise subprocess.TimeoutExpired(comando, timeout_s)
        return ejecutor_ok(comando, timeout_s)

    informe = _correr(models_dir, audio_prueba, ejecutor, ("tiny", "base"))
    assert [r.estado for r in informe.resultados] == [EstadoMedicion.TIMEOUT, EstadoMedicion.OK]


def test_error_devuelve_las_ultimas_lineas_de_stderr(models_dir, audio_prueba):
    crear_modelo_falso(models_dir, "tiny")
    ejecutor = EjecutorFalso(returncode=1, stderr="linea 1\nTraceback\nValueError: audio roto")
    resultado = _correr(models_dir, audio_prueba, ejecutor).resultados[0]
    assert resultado.estado is EstadoMedicion.ERROR
    assert "audio roto" in resultado.detalle


def test_salida_ilegible_es_error(models_dir, audio_prueba):
    crear_modelo_falso(models_dir, "tiny")
    resultado = _correr(models_dir, audio_prueba, EjecutorFalso(stdout="no es json")).resultados[0]
    assert resultado.estado is EstadoMedicion.ERROR


def test_informe_incluye_el_entorno_del_contenedor(models_dir, audio_prueba, ejecutor_ok):
    datos = _correr(models_dir, audio_prueba, ejecutor_ok).como_dict()
    assert datos["entorno"]["cpu_cuota_nucleos"] == 0.1
    assert datos["audio"] == "muestra_es.wav"


def test_comando_agrega_spacy_solo_cuando_se_pide(tmp_path):
    sin = construir_comando(tmp_path, tmp_path / "a.wav", None)
    con = construir_comando(tmp_path, tmp_path / "a.wav", "es_core_news_sm")
    assert "--spacy" not in sin
    assert con[-2:] == ["--spacy", "es_core_news_sm"]
    assert con[1:3] == ["-m", "actaflow_engine.diagnostico.medir"]
