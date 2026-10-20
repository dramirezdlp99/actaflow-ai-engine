"""Extraccion por reglas: numeros, fechas, NIT y las cinco familias de entidades."""

from __future__ import annotations

import re
from datetime import date

import pytest

from actaflow.legal.v1 import entities_pb2 as ent
from actaflow_engine.extraccion.documentos import digito_verificacion_nit
from actaflow_engine.extraccion.extractor import extraer
from actaflow_engine.extraccion.fechas import (
    PATRON_FECHA_TEXTO,
    es_habil,
    fecha_en_texto,
    festivos,
    sumar_dias,
)
from actaflow_engine.extraccion.numeros import cifra_a_numero, palabras_a_numero, sin_tildes

ANA = "11111111-1111-4111-8111-111111111111"
TRANSCRIPCION = """Comparece la convocante María Fernanda López Ruiz, identificada con cédula de ciudadanía número 52.345.678.
También comparece el convocado Inversiones El Roble S.A.S., identificada con NIT 900.123.456-8.
El convocado pagará a la convocante la suma de cuatro millones quinientos mil pesos ($4.500.000) en tres cuotas de $1.500.000.
La primera cuota se pagará el 15 de noviembre de 2026 y la segunda cuota el 15 de diciembre.
El saldo restante se consignará dentro de los treinta (30) días hábiles siguientes.
El convocado entregará las llaves del local a más tardar el 30 de noviembre de 2026.
En caso de incumplimiento, el convocado pagará una cláusula penal de $500.000.
Sobre las sumas en mora se causarán intereses de mora del 2,5 % mensual."""  # noqa: E501


@pytest.mark.parametrize(
    ("texto", "valor"),
    [
        ("un millón quinientos mil", 1_500_000),
        ("cuatro millones quinientos mil", 4_500_000),
        ("mil millones", 1_000_000_000),
        ("ciento un mil", 101_000),
        ("treinta y uno", 31),
        ("dos mil veintiséis", 2026),
        ("veintiún", 21),
        ("casa", None),
    ],
)
def test_palabras_a_numero(texto, valor):
    assert palabras_a_numero(texto) == valor


def test_cifras_con_separadores_colombianos():
    assert cifra_a_numero("1.500.000") == (1_500_000, 0)
    assert cifra_a_numero("1'500.000,5") == (1_500_000, 50)
    assert cifra_a_numero("1.50.0") is None
    assert sin_tildes("Ñandú Cédula") == "nandu cedula"


def test_festivos_y_dias_habiles_de_colombia():
    f2026 = festivos(2026)
    # Ley Emiliani: Todos los Santos (domingo 1) pasa al lunes 2; Cartagena (11) al 16.
    assert date(2026, 11, 2) in f2026
    assert date(2026, 11, 16) in f2026
    assert date(2026, 4, 2) in f2026 and date(2026, 4, 3) in f2026  # jueves y viernes santo
    assert date(2026, 12, 8) in f2026 and date(2026, 7, 20) in f2026
    assert not es_habil(date(2026, 10, 24))  # sabado
    assert sumar_dias(date(2026, 10, 20), 30, habiles=True) == date(2026, 12, 3)
    assert sumar_dias(date(2026, 10, 20), 30, habiles=False) == date(2026, 11, 19)


def test_fechas_escritas_en_texto():
    def fecha(texto):
        return fecha_en_texto(PATRON_FECHA_TEXTO.search(sin_tildes(texto)), date(2026, 10, 20))

    assert fecha("el quince (15) de enero de dos mil veintisiete (2027)") == date(2027, 1, 15)
    assert fecha("el primero de diciembre") == date(2026, 12, 1)
    assert fecha("el 5 de marzo") == date(2027, 3, 5)  # sin anio y ya paso: el siguiente


def test_digito_de_verificacion_del_nit():
    assert digito_verificacion_nit("800197268") == 4  # DIAN
    assert digito_verificacion_nit("860034313") == 7


def test_extrae_las_cinco_familias_de_la_audiencia():
    r = extraer(TRANSCRIPCION, date(2026, 10, 20), [(ANA, "María Fernanda López")])
    assert r.pipeline_version == "reglas-1"

    persona, empresa = (e.party for e in r.parties)
    assert (persona.full_name, persona.document_number, persona.role, persona.participant_id) == (
        "María Fernanda López Ruiz",
        "52345678",
        ent.HEARING_ROLE_CLAIMANT,
        ANA,
    )
    assert persona.document_type == ent.DOCUMENT_TYPE_CEDULA_CIUDADANIA
    assert (empresa.full_name, empresa.is_organization, empresa.document_number) == (
        "Inversiones El Roble S.A.S.",
        True,
        "900123456",
    )
    assert (empresa.nit_check_digit, empresa.nit_check_digit_valid, empresa.role) == (
        "8",
        True,
        ent.HEARING_ROLE_RESPONDENT,
    )

    (monto,) = r.amounts
    assert (monto.amount.amount.units, monto.amount.installments) == (4_500_000, 3)
    assert monto.amount.installment_amount.units == 1_500_000
    assert (monto.amount.debtor_party_index, monto.amount.creditor_party_index) == (1, 0)
    assert monto.amount.written_form == "cuatro millones quinientos mil pesos"
    assert monto.source.segment_index == 2
    linea = TRANSCRIPCION.split("\n")[2]
    assert linea[monto.source.span.start : monto.source.span.end] == monto.source.fragment

    primera, segunda, saldo = (e.deadline for e in r.deadlines)
    assert (primera.due_date.month, primera.due_date.day, primera.installment_number) == (11, 15, 1)
    assert (segunda.due_date.year, segunda.due_date.month, segunda.installment_number) == (
        2026,
        12,
        2,
    )
    assert (saldo.days, saldo.convention, saldo.absolute) == (
        30,
        ent.DAY_COUNT_CONVENTION_BUSINESS_DAYS,
        False,
    )
    assert (saldo.due_date.month, saldo.due_date.day) == (12, 3)
    assert all(e.deadline.amount_index == 0 for e in r.deadlines)

    (compromiso,) = r.commitments
    assert compromiso.commitment.object == "las llaves del local"
    assert compromiso.commitment.obligor_party_index == 1
    assert (compromiso.commitment.due_date.month, compromiso.commitment.due_date.day) == (11, 30)

    clausula, mora = (e.penalty for e in r.penalties)
    assert (clausula.kind, clausula.fixed_amount.units, clausula.trigger) == (
        ent.PENALTY_KIND_FIXED_AMOUNT,
        500_000,
        "incumplimiento",
    )
    assert clausula.obligor_party_index == 1
    assert (mora.kind, mora.basis_points) == (ent.PENALTY_KIND_DEFAULT_INTEREST, 250)
    assert all(0 < e.confidence <= 1 and e.id for e in [*r.parties, *r.amounts, *r.deadlines])


def test_lo_dudoso_queda_para_confirmar():
    r = extraer(
        "Se pagarán 2 millones de pesos en un plazo de 10 días.\n"
        "Acme Ltda., con NIT 900.123.456-1, asiste.",
        date(2026, 10, 20),
    )
    (monto,) = r.amounts
    assert monto.amount.amount.units == 2_000_000
    assert monto.requires_confirmation  # no se sabe quien paga
    (plazo,) = r.deadlines
    assert plazo.deadline.convention == ent.DAY_COUNT_CONVENTION_UNSPECIFIED
    assert plazo.requires_confirmation
    (empresa,) = r.parties
    assert not empresa.party.nit_check_digit_valid and empresa.requires_confirmation


def test_texto_sin_entidades_y_participantes_mencionados_sin_documento():
    vacio = extraer("Buenos días a todos.", date(2026, 10, 20))
    assert not (
        vacio.parties or vacio.amounts or vacio.deadlines or vacio.commitments or vacio.penalties
    )
    r = extraer(
        "Tiene la palabra Carlos Gómez.", date(2026, 10, 20), [(ANA, "Carlos Andrés Gómez")]
    )
    (parte,) = r.parties
    assert parte.party.participant_id == ANA and parte.requires_confirmation
    assert re.fullmatch(r"[0-9a-f-]{36}", parte.id)
