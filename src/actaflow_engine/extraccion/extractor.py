"""Extraccion por reglas de las cinco familias de entidades del caso de estudio.

1. identificacion de las partes      -> PartyIdentification
2. montos acordados                   -> MonetaryAmount
3. plazos de pago                     -> PaymentDeadline
4. compromisos de entrega             -> DeliveryCommitment
5. clausulas penales                  -> PenaltyClause

La IA propone y una persona confirma: cada entidad lleva de donde salio (linea y posicion en la
transcripcion), una confianza y si requiere confirmacion. Las reglas son deterministas, asi el
resultado es explicable y no depende de servicios externos (secreto profesional).

Convencion de la entrada: cada linea del texto es un segmento de la transcripcion
(`SourceReference.segment_index` = numero de linea, desde 0).
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date

from actaflow.common.v1 import values_pb2
from actaflow.legal.v1 import entities_pb2
from actaflow_engine.extraccion.documentos import digito_verificacion_nit, solo_digitos
from actaflow_engine.extraccion.fechas import (
    PATRON_FECHA_NUMERICA,
    PATRON_FECHA_TEXTO,
    fecha_en_texto,
    fecha_numerica,
    sumar_dias,
)
from actaflow_engine.extraccion.numeros import (
    PATRON_PALABRAS,
    cifra_a_numero,
    palabras_a_numero,
    sin_tildes,
)

VERSION = "reglas-1"

_NOMBRE = r"[A-ZÁÉÍÓÚÑ][a-záéíóúñü]+(?:\s+(?:de\s+(?:la\s+|los\s+)?)?[A-ZÁÉÍÓÚÑ][a-záéíóúñü]+){1,4}"
_PERSONA = re.compile(
    rf"(?P<nombre>{_NOMBRE}),?\s+(?:mayor de edad,?\s+)?(?:quien se )?"
    r"identificad[oa]\s+con\s+(?:la\s+|el\s+)?"
    r"(?P<tipo>(?i:c[ée]dula de ciudadan[íi]a|c\.\s?c\.?|cc"
    r"|c[ée]dula de extranjer[íi]a|c\.\s?e\.?|pasaporte))"
    r"\s+(?:(?i:n[úu]mero|no\.?|n\.?[°º])\s*)?(?P<numero>[0-9A-Z][0-9A-Z.]{3,18}[0-9A-Z])",
)
_EMPRESA = re.compile(
    r"(?P<nombre>[A-ZÁÉÍÓÚÑ][\w&]*\.?(?:\s+(?:[A-ZÁÉÍÓÚÑ0-9][\w&]*\.?|de|del|la|las|los|y))*?"
    r"\s(?:S\.?\s?A\.?\s?S\.?|S\.?\s?A\.?|LTDA\.?|Ltda\.?|S\.? en C\.?))"
    r",?\s+(?:identificada\s+)?con\s+(?:el\s+)?NIT\s+(?:n[úu]mero\s+|no\.?\s+)?"
    r"(?P<numero>\d{1,3}(?:[.\s]?\d{3}){2,4})(?:\s?-\s?(?P<dv>\d))?",
)
_ROLES = (
    (re.compile(r"\bconvocante\b"), entities_pb2.HEARING_ROLE_CLAIMANT),
    (re.compile(r"\bconvocad[oa]\b"), entities_pb2.HEARING_ROLE_RESPONDENT),
    (re.compile(r"\bapoderad[oa]\b"), entities_pb2.HEARING_ROLE_ATTORNEY),
    (re.compile(r"\bconciliador[a]?\b"), entities_pb2.HEARING_ROLE_CONCILIATOR),
    (re.compile(r"\btestigo\b"), entities_pb2.HEARING_ROLE_OTHER),
)
_VERBO_PAGO = re.compile(
    r"\b(?:pagara|pagaran|pagar|cancelara|cancelar|abonara|consignara|consignar|transferira|reconocera)\b"
)
_CONTEXTO_PAGO = re.compile(r"\b(?:pag\w*|cuota\w*|cancela\w*|consigna\w*|abon\w*)\b")
_VERBO_ENTREGA = re.compile(r"\b(?:entregara|entregar|restituira|restituir|devolvera|devolver)\b")
_FIN_OBJETO = re.compile(
    r",|;|\.(?:\s|$)|\ba mas tardar\b|\bel dia\b|\bantes del?\b|\bdentro de\b|\ben un plazo\b|$"
)
_PENAL = re.compile(
    r"clausula penal|\bmulta\b|penalidad|\bsancion\b|intereses? de mora|interes(?:es)? moratorios?"
)
_MORA = re.compile(r"intereses? de mora|interes(?:es)? moratorios?")
_PORCENTAJE = re.compile(r"(?P<valor>\d{1,3}(?:,\d{1,2})?)\s*(?:%|por ciento)")
_DISPARADOR = re.compile(r"\b(?:en caso de|si)\s+(?P<texto>[^,;.]{3,200})")
_RELATIVO = re.compile(
    r"\b(?:dentro de|en un plazo de|a mas tardar en|en los)\s+(?:los\s+)?"
    rf"(?P<n>\d{{1,3}}|{PATRON_PALABRAS})"
    r"(?:\s*\(\d{1,3}\))?\s+dias(?:\s+(?P<tipo>habiles|calendarios?))?"
)
_CUOTAS = re.compile(rf"\b(?P<n>\d{{1,3}}|{PATRON_PALABRAS})\s+cuotas\b")
_ORDINALES = {
    "primera": 1, "segunda": 2, "tercera": 3, "cuarta": 4, "quinta": 5, "sexta": 6, "septima": 7,
    "octava": 8, "novena": 9, "decima": 10, "ultima": -1,
}  # fmt: skip
_ORDINAL = re.compile(rf"\b(?P<ord>{'|'.join(_ORDINALES)})\s+cuota\b")
_MONTOS = (
    re.compile(
        r"(?P<moneda>us\$|\$|\bcop\b|\busd\b)\s?"
        r"(?P<cifra>\d{1,3}(?:[.'’ ]\d{3})+|\d+)(?:,(?P<cent>\d{1,2}))?"
    ),
    re.compile(r"\b(?P<cifra>\d{1,3}(?:\.\d{3})+|\d{4,})\s+(?:de\s+)?(?P<moneda>pesos|dolares)\b"),
    re.compile(
        r"\b(?P<num>\d{1,3}(?:,\d{1,2})?)\s+(?P<escala>millones|millon|mil)\s+(?:de\s+)?(?P<moneda>pesos|dolares)\b"
    ),
    re.compile(rf"(?P<palabras>{PATRON_PALABRAS})\s+(?:de\s+)?(?P<moneda>pesos|dolares)\b"),
)
_MAXIMOS = {"parties": 50, "amounts": 200, "deadlines": 200, "commitments": 200, "penalties": 50}


@dataclass
class Oracion:
    linea: int
    inicio: int  # posicion dentro de la linea
    texto: str
    normal: str  # minusculas y sin tildes, misma longitud


@dataclass
class _Parte:
    entidad: entities_pb2.LegalEntity
    claves: list[str] = field(default_factory=list)  # formas normalizadas del nombre


@dataclass
class _Monto:
    valor: int
    centavos: int
    moneda: str
    inicio: int
    fin: int


def oraciones(texto: str) -> list[Oracion]:
    """Divide cada linea en oraciones sin romper cifras (1.500.000) ni siglas (S.A.S.)."""
    resultado = []
    for numero, linea in enumerate(texto.split("\n")):
        inicio = 0
        for corte in re.finditer(r"(?<=[.;!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡])", linea):
            resultado.append(Oracion(numero, inicio, linea[inicio : corte.start()], ""))
            inicio = corte.end()
        resultado.append(Oracion(numero, inicio, linea[inicio:], ""))
    for oracion in resultado:
        oracion.normal = sin_tildes(oracion.texto)
    return [o for o in resultado if o.texto.strip()]


def _dinero(valor: int, centavos: int, moneda: str) -> values_pb2.Money:
    return values_pb2.Money(currency_code=moneda, units=valor, nanos=centavos * 10_000_000)


def _fecha(dia: date) -> values_pb2.CalendarDate:
    return values_pb2.CalendarDate(year=dia.year, month=dia.month, day=dia.day)


def _fuente(oracion: Oracion, inicio: int, fin: int) -> entities_pb2.SourceReference:
    return entities_pb2.SourceReference(
        segment_index=oracion.linea,
        span=values_pb2.TextSpan(start=oracion.inicio + inicio, end=oracion.inicio + fin),
        fragment=oracion.texto[inicio:fin][:2000],
    )


def _entidad(
    confianza: float, requiere: bool, fuente: entities_pb2.SourceReference
) -> entities_pb2.LegalEntity:
    return entities_pb2.LegalEntity(
        id=str(uuid.uuid4()),
        source=fuente,
        confidence=round(confianza, 2),
        requires_confirmation=requiere,
    )


def _clave_nombre(nombre: str) -> list[str]:
    """Formas para encontrar a una persona: nombre completo y nombre + apellido."""
    palabras = [p for p in sin_tildes(nombre).split() if p not in ("de", "la", "los", "del")]
    claves = [" ".join(palabras)]
    if len(palabras) >= 3:
        claves.append(f"{palabras[0]} {palabras[-2]}")
        claves.append(f"{palabras[0]} {palabras[-1]}")
    if len(palabras) >= 2:
        claves.append(f"{palabras[0]} {palabras[1]}")
    return claves


def _rol_cercano(oracion: Oracion, inicio: int, fin: int) -> int:
    """Rol mas cercano al nombre dentro de la oracion."""
    mejor = (10**9, entities_pb2.HEARING_ROLE_UNSPECIFIED)
    for patron, rol in _ROLES:
        for c in patron.finditer(oracion.normal):
            distancia = c.start() - fin if c.start() >= fin else inicio - c.end()
            mejor = min(mejor, (distancia, rol))
    return mejor[1] if mejor[0] < 120 else entities_pb2.HEARING_ROLE_UNSPECIFIED


class Extractor:
    def __init__(self, texto: str, referencia: date, participantes: Iterable[tuple[str, str]] = ()):
        self.texto = texto
        self.referencia = referencia
        self.participantes = list(participantes)
        self.oraciones = oraciones(texto)
        self.partes: list[_Parte] = []
        self.resultado = entities_pb2.EntityExtractionResult(
            reference_date=_fecha(referencia), pipeline_version=VERSION
        )

    # ------------------------------------------------------------------ partes

    def _participante(self, nombre: str) -> str:
        claves = set(_clave_nombre(nombre))
        for participante_id, registrado in self.participantes:
            if claves & set(_clave_nombre(registrado)):
                return participante_id
        return ""

    def _agregar_parte(
        self,
        oracion: Oracion,
        coincidencia: re.Match[str],
        parte: entities_pb2.PartyIdentification,
        confianza: float,
        requiere: bool,
    ) -> None:
        clave = (parte.document_type, parte.document_number) if parte.document_number else None
        for existente in self.partes:
            p = existente.entidad.party
            if clave and (p.document_type, p.document_number) == clave:
                return
            if not clave and set(_clave_nombre(parte.full_name)) & set(existente.claves):
                return
        entidad = _entidad(
            confianza, requiere, _fuente(oracion, coincidencia.start(), coincidencia.end())
        )
        entidad.party.CopyFrom(parte)
        self.partes.append(_Parte(entidad, _clave_nombre(parte.full_name)))

    def extraer_partes(self) -> None:
        for oracion in self.oraciones:
            for c in _PERSONA.finditer(oracion.texto):
                tipo_texto = sin_tildes(c.group("tipo")).replace(" ", "")
                tipo = (
                    entities_pb2.DOCUMENT_TYPE_PASSPORT
                    if tipo_texto.startswith("pasaporte")
                    else entities_pb2.DOCUMENT_TYPE_CEDULA_EXTRANJERIA
                    if "extranjer" in tipo_texto or tipo_texto.startswith("c.e")
                    else entities_pb2.DOCUMENT_TYPE_CEDULA_CIUDADANIA
                )
                numero = re.sub(r"[.\s]", "", c.group("numero")).upper()
                if tipo != entities_pb2.DOCUMENT_TYPE_PASSPORT:
                    numero = solo_digitos(numero)
                nombre = " ".join(c.group("nombre").split())
                parte = entities_pb2.PartyIdentification(
                    full_name=nombre,
                    document_type=tipo,
                    document_number=numero[:20],
                    role=_rol_cercano(oracion, c.start(), c.end()),
                    participant_id=self._participante(nombre),
                )
                self._agregar_parte(
                    oracion, c, parte, 0.9, parte.role == entities_pb2.HEARING_ROLE_UNSPECIFIED
                )
            for c in _EMPRESA.finditer(oracion.texto):
                base = solo_digitos(c.group("numero"))
                dv = c.group("dv") or ""
                valido = bool(dv) and digito_verificacion_nit(base) == int(dv)
                nombre = " ".join(c.group("nombre").split())
                parte = entities_pb2.PartyIdentification(
                    full_name=nombre,
                    is_organization=True,
                    document_type=entities_pb2.DOCUMENT_TYPE_NIT,
                    document_number=base[:20],
                    nit_check_digit=dv,
                    nit_check_digit_valid=valido,
                    role=_rol_cercano(oracion, c.start(), c.end()),
                    participant_id=self._participante(nombre),
                )
                self._agregar_parte(oracion, c, parte, 0.9 if valido else 0.6, not valido)
        # Participantes registrados que se mencionan sin documento.
        for participante_id, registrado in self.participantes:
            if any(p.entidad.party.participant_id == participante_id for p in self.partes):
                continue
            for clave in _clave_nombre(registrado):
                encontrado = next(
                    (
                        (o, m)
                        for o in self.oraciones
                        for m in re.finditer(rf"\b{re.escape(clave)}\b", o.normal)
                    ),
                    None,
                )
                if encontrado:
                    oracion, m = encontrado
                    parte = entities_pb2.PartyIdentification(
                        full_name=registrado,
                        role=_rol_cercano(oracion, m.start(), m.end()),
                        participant_id=participante_id,
                    )
                    self._agregar_parte(oracion, m, parte, 0.6, True)
                    break

    def _menciones(self, oracion: Oracion) -> list[tuple[int, int]]:
        """(posicion, indice de parte) de cada mencion de una parte, por nombre o por rol."""
        menciones = []
        for indice, parte in enumerate(self.partes):
            for clave in parte.claves:
                menciones += [
                    (m.start(), indice)
                    for m in re.finditer(rf"\b{re.escape(clave)}\b", oracion.normal)
                ]
        for patron, rol in _ROLES:
            indice = next((i for i, p in enumerate(self.partes) if p.entidad.party.role == rol), -1)
            if indice >= 0:
                menciones += [(m.start(), indice) for m in patron.finditer(oracion.normal)]
        return sorted(set(menciones))

    def _antes_y_despues(self, oracion: Oracion, verbo: re.Match[str] | None) -> tuple[int, int]:
        if not verbo:
            return -1, -1
        menciones = self._menciones(oracion)
        antes = [i for pos, i in menciones if pos < verbo.start()]
        despues = [i for pos, i in menciones if pos > verbo.end()]
        deudor = antes[-1] if antes else -1
        acreedor = next((i for i in despues if i != deudor), -1)
        return deudor, acreedor

    # ------------------------------------------------------------------ montos

    @staticmethod
    def _montos(oracion: Oracion) -> list[_Monto]:
        encontrados: list[_Monto] = []
        for patron in _MONTOS:
            for c in patron.finditer(oracion.normal):
                grupos = c.groupdict()
                moneda = "USD" if grupos.get("moneda") in ("us$", "usd", "dolares") else "COP"
                if grupos.get("cifra"):
                    cifra = cifra_a_numero(
                        grupos["cifra"] + (f",{grupos['cent']}" if grupos.get("cent") else "")
                    )
                    if not cifra:
                        continue
                    valor, centavos = cifra
                elif grupos.get("num"):
                    escala = 1_000 if grupos["escala"] == "mil" else 1_000_000
                    valor, centavos = round(float(grupos["num"].replace(",", ".")) * escala), 0
                else:
                    numero = palabras_a_numero(grupos["palabras"])
                    if numero is None:
                        continue
                    valor, centavos = numero, 0
                if valor <= 0 or any(m.inicio < c.end() and c.start() < m.fin for m in encontrados):
                    continue
                encontrados.append(_Monto(valor, centavos, moneda, c.start(), c.end()))
        encontrados.sort(key=lambda m: m.inicio)
        # "un millon de pesos ($1.000.000)": la misma cifra dicha dos veces es un solo monto.
        unicos: list[_Monto] = []
        for monto in encontrados:
            if not any(
                (u.valor, u.centavos, u.moneda) == (monto.valor, monto.centavos, monto.moneda)
                for u in unicos
            ):
                unicos.append(monto)
        return unicos

    def _extraer_montos(self, oracion: Oracion, montos: list[_Monto]) -> list[int]:
        """Agrega los montos de la oracion; devuelve sus indices en `amounts`."""
        if not montos:
            return []
        deudor, acreedor = self._antes_y_despues(oracion, _VERBO_PAGO.search(oracion.normal))
        cuotas_match = _CUOTAS.search(oracion.normal)
        cuotas = 0
        if cuotas_match:
            n = cuotas_match.group("n")
            cuotas = int(n) if n.isdigit() else palabras_a_numero(n) or 0
        indices = []
        restantes = list(montos)
        if cuotas > 1:
            total = max(restantes, key=lambda m: m.valor)
            por_cuota = next(
                (m for m in restantes if m is not total and m.inicio > cuotas_match.start()), None
            )
            if por_cuota is None and total.inicio > cuotas_match.start():
                por_cuota, total = total, None
            entidad = _entidad(
                0.85,
                deudor < 0,
                _fuente(oracion, (total or por_cuota).inicio, max(m.fin for m in restantes)),
            )
            monto = entidad.amount
            if total is not None:
                monto.amount.CopyFrom(_dinero(total.valor, total.centavos, total.moneda))
            else:
                monto.amount.CopyFrom(_dinero(por_cuota.valor * cuotas, 0, por_cuota.moneda))
            if por_cuota is not None:
                monto.installment_amount.CopyFrom(
                    _dinero(por_cuota.valor, por_cuota.centavos, por_cuota.moneda)
                )
            monto.installments = cuotas
            monto.written_form = oracion.texto[
                (total or por_cuota).inicio : (total or por_cuota).fin
            ]
            monto.debtor_party_index, monto.creditor_party_index = deudor, acreedor
            self.resultado.amounts.append(entidad)
            indices.append(len(self.resultado.amounts) - 1)
            restantes = [m for m in restantes if m is not total and m is not por_cuota]
        for m in restantes:
            entidad = _entidad(0.85, deudor < 0, _fuente(oracion, m.inicio, m.fin))
            entidad.amount.amount.CopyFrom(_dinero(m.valor, m.centavos, m.moneda))
            entidad.amount.written_form = oracion.texto[m.inicio : m.fin]
            entidad.amount.debtor_party_index, entidad.amount.creditor_party_index = (
                deudor,
                acreedor,
            )
            self.resultado.amounts.append(entidad)
            indices.append(len(self.resultado.amounts) - 1)
        return indices

    # ------------------------------------------------------------------ plazos

    def _fechas(self, oracion: Oracion) -> list[tuple[re.Match[str], date]]:
        fechas = []
        for c in PATRON_FECHA_TEXTO.finditer(oracion.normal):
            dia = fecha_en_texto(c, self.referencia)
            if dia:
                fechas.append((c, dia))
        for c in PATRON_FECHA_NUMERICA.finditer(oracion.normal):
            dia = fecha_numerica(c)
            if dia:
                fechas.append((c, dia))
        return sorted(fechas, key=lambda f: f[0].start())

    def _relativos(self, oracion: Oracion) -> list[tuple[re.Match[str], int, int, date]]:
        relativos = []
        for c in _RELATIVO.finditer(oracion.normal):
            n = c.group("n")
            dias = int(n) if n.isdigit() else palabras_a_numero(n)
            if not dias:
                continue
            tipo = c.group("tipo") or ""
            convencion = (
                entities_pb2.DAY_COUNT_CONVENTION_BUSINESS_DAYS
                if tipo == "habiles"
                else entities_pb2.DAY_COUNT_CONVENTION_CALENDAR_DAYS
                if tipo.startswith("calendario")
                else entities_pb2.DAY_COUNT_CONVENTION_UNSPECIFIED
            )
            habiles = convencion == entities_pb2.DAY_COUNT_CONVENTION_BUSINESS_DAYS
            relativos.append((c, dias, convencion, sumar_dias(self.referencia, dias, habiles)))
        return relativos

    def _extraer_plazos(self, oracion: Oracion, montos: list[int]) -> None:
        if not _CONTEXTO_PAGO.search(oracion.normal) or _VERBO_ENTREGA.search(oracion.normal):
            return
        inferido = not montos
        monto = montos[0] if montos else len(self.resultado.amounts) - 1
        for c, dia in self._fechas(oracion):
            entidad = _entidad(0.85, inferido, _fuente(oracion, c.start(), c.end()))
            plazo = entidad.deadline
            plazo.due_date.CopyFrom(_fecha(dia))
            plazo.expression = oracion.texto[c.start() : c.end()]
            plazo.absolute = True
            plazo.amount_index = monto
            ordinal = None
            for o in _ORDINAL.finditer(oracion.normal[max(0, c.start() - 60) : c.start()]):
                ordinal = o
            if ordinal:
                plazo.installment_number = max(0, _ORDINALES[ordinal.group("ord")])
            self.resultado.deadlines.append(entidad)
        for c, dias, convencion, vence in self._relativos(oracion):
            sin_convencion = convencion == entities_pb2.DAY_COUNT_CONVENTION_UNSPECIFIED
            entidad = _entidad(
                0.75, sin_convencion or inferido, _fuente(oracion, c.start(), c.end())
            )
            plazo = entidad.deadline
            plazo.due_date.CopyFrom(_fecha(vence))
            plazo.expression = oracion.texto[c.start() : c.end()]
            plazo.days = dias
            plazo.convention = convencion
            plazo.amount_index = monto
            self.resultado.deadlines.append(entidad)

    # ------------------------------------------------------------------ compromisos

    def _extraer_compromisos(self, oracion: Oracion) -> None:
        verbo = _VERBO_ENTREGA.search(oracion.normal)
        if not verbo:
            return
        deudor, _ = self._antes_y_despues(oracion, verbo)
        resto = oracion.normal[verbo.end() :]
        fin_objeto = _FIN_OBJETO.search(resto)
        corte = verbo.end() + (fin_objeto.start() if fin_objeto else len(resto))
        objeto = oracion.texto[verbo.end() : corte].strip()
        if not objeto:
            return
        entidad = _entidad(
            0.7, deudor < 0, _fuente(oracion, verbo.start(), len(oracion.texto.rstrip(" .")))
        )
        compromiso = entidad.commitment
        compromiso.obligor_party_index = deudor
        compromiso.object = objeto[:500]
        fechas = [f for f in self._fechas(oracion) if f[0].start() >= verbo.start()]
        relativos = [r for r in self._relativos(oracion) if r[0].start() >= verbo.start()]
        if fechas:
            c, dia = fechas[0]
            compromiso.due_date.CopyFrom(_fecha(dia))
            compromiso.deadline_expression = oracion.texto[c.start() : c.end()]
        elif relativos:
            c, _, _, vence = relativos[0]
            compromiso.due_date.CopyFrom(_fecha(vence))
            compromiso.deadline_expression = oracion.texto[c.start() : c.end()]
        self.resultado.commitments.append(entidad)

    # ------------------------------------------------------------------ clausulas penales

    def _extraer_penalidad(self, oracion: Oracion, montos: list[_Monto]) -> bool:
        penal = _PENAL.search(oracion.normal)
        if not penal:
            return False
        deudor, _ = self._antes_y_despues(oracion, _VERBO_PAGO.search(oracion.normal))
        entidad = _entidad(0.75, deudor < 0, _fuente(oracion, 0, len(oracion.texto.rstrip(" "))))
        clausula = entidad.penalty
        porcentaje = _PORCENTAJE.search(oracion.normal)
        if _MORA.search(oracion.normal):
            clausula.kind = entities_pb2.PENALTY_KIND_DEFAULT_INTEREST
        elif porcentaje:
            clausula.kind = entities_pb2.PENALTY_KIND_PERCENTAGE
        elif montos:
            clausula.kind = entities_pb2.PENALTY_KIND_FIXED_AMOUNT
        if porcentaje:
            clausula.basis_points = min(
                100_000, round(float(porcentaje.group("valor").replace(",", ".")) * 100)
            )
        if montos:
            clausula.fixed_amount.CopyFrom(
                _dinero(montos[0].valor, montos[0].centavos, montos[0].moneda)
            )
        disparador = _DISPARADOR.search(oracion.normal)
        if disparador:
            clausula.trigger = oracion.texto[
                disparador.start("texto") : disparador.end("texto")
            ].strip()[:500]
        clausula.obligor_party_index = deudor
        self.resultado.penalties.append(entidad)
        return True

    # ------------------------------------------------------------------ todo

    def ejecutar(self) -> entities_pb2.EntityExtractionResult:
        self.extraer_partes()
        for oracion in self.oraciones:
            montos = self._montos(oracion)
            if self._extraer_penalidad(oracion, montos):
                continue
            indices = self._extraer_montos(oracion, montos)
            self._extraer_plazos(oracion, indices)
            self._extraer_compromisos(oracion)
        self.resultado.parties.extend(p.entidad for p in self.partes)
        for campo, maximo in _MAXIMOS.items():
            lista = getattr(self.resultado, campo)
            del lista[maximo:]
        return self.resultado


def extraer(
    texto: str, referencia: date, participantes: Iterable[tuple[str, str]] = ()
) -> entities_pb2.EntityExtractionResult:  # noqa: E501
    """Extrae las cinco familias de entidades de una transcripcion."""
    return Extractor(texto, referencia, participantes).ejecutar()
