"""Convierte el HTML restringido de un acta en PDF con fpdf2, sin tocar el disco.

El HTML viene del lenguaje de plantillas (llenado en el navegador): solo h2, h3, p, br, strong,
span.valor y mark.falta. Aun asi se vuelve a filtrar aqui: cualquier otra etiqueta o atributo se
descarta y queda solo su texto. Las fuentes base del PDF son Latin-1 (alcanzan para el espanol);
la puntuacion tipografica se cambia por su equivalente y lo demas por "?".
"""

from __future__ import annotations

import html
from html.parser import HTMLParser

from fpdf import FPDF

PERMITIDAS = {"h2", "h3", "p", "br", "strong", "b"}
EQUIVALENTES = str.maketrans(
    {
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "–": "-",
        "—": "-",
        "…": "...",
        "•": "-",
        " ": " ",
        " ": " ",
        " ": " ",
    }
)
MAX_PAGINAS = 200


class DocumentoDemasiadoLargoError(ValueError):
    """El acta pasa del tope de paginas (proteccion de memoria en Render Free)."""


def latin1(texto: str) -> str:
    return texto.translate(EQUIVALENTES).encode("latin-1", "replace").decode("latin-1")


class _Filtro(HTMLParser):
    """Deja solo las etiquetas permitidas, sin atributos; `mark` (dato que falta) va entre []."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.salida: list[str] = []

    def handle_starttag(self, etiqueta: str, atributos) -> None:  # noqa: ANN001
        if etiqueta == "br":
            self.salida.append("<br>")
        elif etiqueta in PERMITIDAS:
            self.salida.append(f"<{'b' if etiqueta == 'strong' else etiqueta}>")
        elif etiqueta == "mark":
            self.salida.append("[")

    def handle_endtag(self, etiqueta: str) -> None:
        if etiqueta in PERMITIDAS and etiqueta != "br":
            self.salida.append(f"</{'b' if etiqueta == 'strong' else etiqueta}>")
        elif etiqueta == "mark":
            self.salida.append("]")

    def handle_data(self, datos: str) -> None:
        self.salida.append(html.escape(latin1(datos), quote=False))


def html_seguro(fuente: str) -> str:
    filtro = _Filtro()
    filtro.feed(fuente)
    filtro.close()
    return "".join(filtro.salida)


class _Acta(FPDF):
    def __init__(self, titulo: str) -> None:
        super().__init__(format="Letter")
        self._titulo = latin1(titulo)

    def header(self) -> None:
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(90, 90, 90)
        self.cell(0, 6, self._titulo, align="L", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def footer(self) -> None:
        self.set_y(-18)
        self.set_font("Helvetica", size=8)
        self.set_text_color(90, 90, 90)
        self.cell(
            0,
            6,
            f"ActaFlow - Pagina {self.page_no()} de {{nb}} - Sello verificable en /verificar",
            align="C",
        )


def renderizar(titulo: str, fuente_html: str) -> tuple[bytes, int]:
    """PDF (carta, margenes de 25 mm) y su numero de paginas."""
    pdf = _Acta(titulo or "Acta")
    pdf.set_title(latin1(titulo or "Acta"))
    pdf.set_creator("ActaFlow")
    pdf.set_margins(25, 22, 25)
    pdf.set_auto_page_break(auto=True, margin=22)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    pdf.write_html(html_seguro(fuente_html))
    if pdf.pages_count > MAX_PAGINAS:
        raise DocumentoDemasiadoLargoError(f"El acta tiene mas de {MAX_PAGINAS} paginas")
    return bytes(pdf.output()), pdf.pages_count
