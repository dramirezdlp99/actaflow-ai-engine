from __future__ import annotations

import pytest

from actaflow_engine.diagnostico.wer import distancia_edicion, normalizar, wer


def test_normalizar_quita_tildes_mayusculas_y_puntuacion():
    assert normalizar("¡Audiencia de CONCILIACIÓN, señora López!") == [
        "audiencia",
        "de",
        "conciliacion",
        "senora",
        "lopez",
    ]


def test_textos_iguales_tienen_wer_cero_aunque_cambie_la_puntuacion():
    assert wer("Un millón de pesos.", "un millon de pesos") == 0.0


@pytest.mark.parametrize(
    ("referencia", "hipotesis", "esperado"),
    [
        ("pagara tres cuotas", "pagara dos cuotas", 1 / 3),
        ("pagara tres cuotas", "pagara cuotas", 1 / 3),
        ("pagara tres cuotas", "pagara tres cuotas mensuales", 1 / 3),
        ("multa del diez por ciento", "", 1.0),
    ],
)
def test_wer_cuenta_sustituciones_borrados_e_inserciones(referencia, hipotesis, esperado):
    assert wer(referencia, hipotesis) == pytest.approx(esperado)


def test_wer_sin_referencia():
    assert wer("", "") == 0.0
    assert wer("", "algo") == 1.0


def test_distancia_edicion_es_simetrica_en_longitud():
    assert distancia_edicion(["a", "b", "c"], ["c", "b", "a"]) == 2
