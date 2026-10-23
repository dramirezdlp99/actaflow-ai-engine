"""El acta en PDF: solo el HTML permitido, texto en Latin-1 y tope de paginas."""

from __future__ import annotations

import pytest

from actaflow_engine.documentos import pdf
from actaflow_engine.documentos.pdf import html_seguro, latin1, renderizar


def test_deja_solo_las_etiquetas_permitidas_y_sin_atributos():
    fuente = (
        '<h2 onclick="x()">Acta</h2><p>Monto: <span class="valor">$ 1.500.000</span> '
        '<mark class="falta">acuerdo.plazo</mark><script>alert(1)</script><img src=x></p>'
        "<p>A &amp; B<br>C</p>"
    )
    assert html_seguro(fuente) == (
        "<h2>Acta</h2><p>Monto: $ 1.500.000 [acuerdo.plazo]alert(1)</p><p>A &amp; B<br>C</p>"
    )


def test_cambia_la_puntuacion_tipografica_y_conserva_tildes_y_enes():
    assert latin1("“Ñoño” – José… π") == '"Ñoño" - José... ?'


def test_genera_un_pdf_de_varias_paginas_con_encabezado_y_pie():
    cuerpo = "".join(f"<p>Parrafo {i} del acuerdo de conciliación.</p>" for i in range(120))
    datos, paginas = renderizar("Acta CC-2026-0400", f"<h2>ACTA</h2>{cuerpo}")
    assert datos.startswith(b"%PDF-")
    assert paginas >= 3


def test_rechaza_un_acta_desmedida(monkeypatch):
    monkeypatch.setattr(pdf, "MAX_PAGINAS", 1)
    with pytest.raises(pdf.DocumentoDemasiadoLargoError):
        renderizar("Acta", "".join(f"<p>Parrafo {i}</p>" for i in range(200)))
