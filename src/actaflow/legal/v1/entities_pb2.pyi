from actaflow.common.v1 import values_pb2 as _values_pb2
from buf.validate import validate_pb2 as _validate_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DocumentType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DOCUMENT_TYPE_UNSPECIFIED: _ClassVar[DocumentType]
    DOCUMENT_TYPE_CEDULA_CIUDADANIA: _ClassVar[DocumentType]
    DOCUMENT_TYPE_CEDULA_EXTRANJERIA: _ClassVar[DocumentType]
    DOCUMENT_TYPE_NIT: _ClassVar[DocumentType]
    DOCUMENT_TYPE_PASSPORT: _ClassVar[DocumentType]

class HearingRole(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    HEARING_ROLE_UNSPECIFIED: _ClassVar[HearingRole]
    HEARING_ROLE_CLAIMANT: _ClassVar[HearingRole]
    HEARING_ROLE_RESPONDENT: _ClassVar[HearingRole]
    HEARING_ROLE_ATTORNEY: _ClassVar[HearingRole]
    HEARING_ROLE_CONCILIATOR: _ClassVar[HearingRole]
    HEARING_ROLE_OTHER: _ClassVar[HearingRole]

class DayCountConvention(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DAY_COUNT_CONVENTION_UNSPECIFIED: _ClassVar[DayCountConvention]
    DAY_COUNT_CONVENTION_BUSINESS_DAYS: _ClassVar[DayCountConvention]
    DAY_COUNT_CONVENTION_CALENDAR_DAYS: _ClassVar[DayCountConvention]

class PenaltyKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PENALTY_KIND_UNSPECIFIED: _ClassVar[PenaltyKind]
    PENALTY_KIND_FIXED_AMOUNT: _ClassVar[PenaltyKind]
    PENALTY_KIND_PERCENTAGE: _ClassVar[PenaltyKind]
    PENALTY_KIND_DEFAULT_INTEREST: _ClassVar[PenaltyKind]

class ReviewState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    REVIEW_STATE_UNSPECIFIED: _ClassVar[ReviewState]
    REVIEW_STATE_CONFIRMED: _ClassVar[ReviewState]
    REVIEW_STATE_CORRECTED: _ClassVar[ReviewState]
    REVIEW_STATE_REJECTED: _ClassVar[ReviewState]
DOCUMENT_TYPE_UNSPECIFIED: DocumentType
DOCUMENT_TYPE_CEDULA_CIUDADANIA: DocumentType
DOCUMENT_TYPE_CEDULA_EXTRANJERIA: DocumentType
DOCUMENT_TYPE_NIT: DocumentType
DOCUMENT_TYPE_PASSPORT: DocumentType
HEARING_ROLE_UNSPECIFIED: HearingRole
HEARING_ROLE_CLAIMANT: HearingRole
HEARING_ROLE_RESPONDENT: HearingRole
HEARING_ROLE_ATTORNEY: HearingRole
HEARING_ROLE_CONCILIATOR: HearingRole
HEARING_ROLE_OTHER: HearingRole
DAY_COUNT_CONVENTION_UNSPECIFIED: DayCountConvention
DAY_COUNT_CONVENTION_BUSINESS_DAYS: DayCountConvention
DAY_COUNT_CONVENTION_CALENDAR_DAYS: DayCountConvention
PENALTY_KIND_UNSPECIFIED: PenaltyKind
PENALTY_KIND_FIXED_AMOUNT: PenaltyKind
PENALTY_KIND_PERCENTAGE: PenaltyKind
PENALTY_KIND_DEFAULT_INTEREST: PenaltyKind
REVIEW_STATE_UNSPECIFIED: ReviewState
REVIEW_STATE_CONFIRMED: ReviewState
REVIEW_STATE_CORRECTED: ReviewState
REVIEW_STATE_REJECTED: ReviewState

class SourceReference(_message.Message):
    __slots__ = ("segment_index", "span", "fragment")
    SEGMENT_INDEX_FIELD_NUMBER: _ClassVar[int]
    SPAN_FIELD_NUMBER: _ClassVar[int]
    FRAGMENT_FIELD_NUMBER: _ClassVar[int]
    segment_index: int
    span: _values_pb2.TextSpan
    fragment: str
    def __init__(self, segment_index: _Optional[int] = ..., span: _Optional[_Union[_values_pb2.TextSpan, _Mapping]] = ..., fragment: _Optional[str] = ...) -> None: ...

class PartyIdentification(_message.Message):
    __slots__ = ("full_name", "is_organization", "document_type", "document_number", "nit_check_digit", "nit_check_digit_valid", "role", "participant_id")
    FULL_NAME_FIELD_NUMBER: _ClassVar[int]
    IS_ORGANIZATION_FIELD_NUMBER: _ClassVar[int]
    DOCUMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    DOCUMENT_NUMBER_FIELD_NUMBER: _ClassVar[int]
    NIT_CHECK_DIGIT_FIELD_NUMBER: _ClassVar[int]
    NIT_CHECK_DIGIT_VALID_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    PARTICIPANT_ID_FIELD_NUMBER: _ClassVar[int]
    full_name: str
    is_organization: bool
    document_type: DocumentType
    document_number: str
    nit_check_digit: str
    nit_check_digit_valid: bool
    role: HearingRole
    participant_id: str
    def __init__(self, full_name: _Optional[str] = ..., is_organization: _Optional[bool] = ..., document_type: _Optional[_Union[DocumentType, str]] = ..., document_number: _Optional[str] = ..., nit_check_digit: _Optional[str] = ..., nit_check_digit_valid: _Optional[bool] = ..., role: _Optional[_Union[HearingRole, str]] = ..., participant_id: _Optional[str] = ...) -> None: ...

class MonetaryAmount(_message.Message):
    __slots__ = ("amount", "written_form", "installments", "installment_amount", "debtor_party_index", "creditor_party_index")
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    WRITTEN_FORM_FIELD_NUMBER: _ClassVar[int]
    INSTALLMENTS_FIELD_NUMBER: _ClassVar[int]
    INSTALLMENT_AMOUNT_FIELD_NUMBER: _ClassVar[int]
    DEBTOR_PARTY_INDEX_FIELD_NUMBER: _ClassVar[int]
    CREDITOR_PARTY_INDEX_FIELD_NUMBER: _ClassVar[int]
    amount: _values_pb2.Money
    written_form: str
    installments: int
    installment_amount: _values_pb2.Money
    debtor_party_index: int
    creditor_party_index: int
    def __init__(self, amount: _Optional[_Union[_values_pb2.Money, _Mapping]] = ..., written_form: _Optional[str] = ..., installments: _Optional[int] = ..., installment_amount: _Optional[_Union[_values_pb2.Money, _Mapping]] = ..., debtor_party_index: _Optional[int] = ..., creditor_party_index: _Optional[int] = ...) -> None: ...

class PaymentDeadline(_message.Message):
    __slots__ = ("due_date", "expression", "absolute", "days", "convention", "amount_index", "installment_number")
    DUE_DATE_FIELD_NUMBER: _ClassVar[int]
    EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    ABSOLUTE_FIELD_NUMBER: _ClassVar[int]
    DAYS_FIELD_NUMBER: _ClassVar[int]
    CONVENTION_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_INDEX_FIELD_NUMBER: _ClassVar[int]
    INSTALLMENT_NUMBER_FIELD_NUMBER: _ClassVar[int]
    due_date: _values_pb2.CalendarDate
    expression: str
    absolute: bool
    days: int
    convention: DayCountConvention
    amount_index: int
    installment_number: int
    def __init__(self, due_date: _Optional[_Union[_values_pb2.CalendarDate, _Mapping]] = ..., expression: _Optional[str] = ..., absolute: _Optional[bool] = ..., days: _Optional[int] = ..., convention: _Optional[_Union[DayCountConvention, str]] = ..., amount_index: _Optional[int] = ..., installment_number: _Optional[int] = ...) -> None: ...

class DeliveryCommitment(_message.Message):
    __slots__ = ("obligor_party_index", "object", "due_date", "deadline_expression")
    OBLIGOR_PARTY_INDEX_FIELD_NUMBER: _ClassVar[int]
    OBJECT_FIELD_NUMBER: _ClassVar[int]
    DUE_DATE_FIELD_NUMBER: _ClassVar[int]
    DEADLINE_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    obligor_party_index: int
    object: str
    due_date: _values_pb2.CalendarDate
    deadline_expression: str
    def __init__(self, obligor_party_index: _Optional[int] = ..., object: _Optional[str] = ..., due_date: _Optional[_Union[_values_pb2.CalendarDate, _Mapping]] = ..., deadline_expression: _Optional[str] = ...) -> None: ...

class PenaltyClause(_message.Message):
    __slots__ = ("kind", "fixed_amount", "basis_points", "trigger", "obligor_party_index")
    KIND_FIELD_NUMBER: _ClassVar[int]
    FIXED_AMOUNT_FIELD_NUMBER: _ClassVar[int]
    BASIS_POINTS_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_FIELD_NUMBER: _ClassVar[int]
    OBLIGOR_PARTY_INDEX_FIELD_NUMBER: _ClassVar[int]
    kind: PenaltyKind
    fixed_amount: _values_pb2.Money
    basis_points: int
    trigger: str
    obligor_party_index: int
    def __init__(self, kind: _Optional[_Union[PenaltyKind, str]] = ..., fixed_amount: _Optional[_Union[_values_pb2.Money, _Mapping]] = ..., basis_points: _Optional[int] = ..., trigger: _Optional[str] = ..., obligor_party_index: _Optional[int] = ...) -> None: ...

class LegalEntity(_message.Message):
    __slots__ = ("id", "party", "amount", "deadline", "commitment", "penalty", "source", "confidence", "requires_confirmation", "review")
    ID_FIELD_NUMBER: _ClassVar[int]
    PARTY_FIELD_NUMBER: _ClassVar[int]
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    DEADLINE_FIELD_NUMBER: _ClassVar[int]
    COMMITMENT_FIELD_NUMBER: _ClassVar[int]
    PENALTY_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    REQUIRES_CONFIRMATION_FIELD_NUMBER: _ClassVar[int]
    REVIEW_FIELD_NUMBER: _ClassVar[int]
    id: str
    party: PartyIdentification
    amount: MonetaryAmount
    deadline: PaymentDeadline
    commitment: DeliveryCommitment
    penalty: PenaltyClause
    source: SourceReference
    confidence: float
    requires_confirmation: bool
    review: ReviewState
    def __init__(self, id: _Optional[str] = ..., party: _Optional[_Union[PartyIdentification, _Mapping]] = ..., amount: _Optional[_Union[MonetaryAmount, _Mapping]] = ..., deadline: _Optional[_Union[PaymentDeadline, _Mapping]] = ..., commitment: _Optional[_Union[DeliveryCommitment, _Mapping]] = ..., penalty: _Optional[_Union[PenaltyClause, _Mapping]] = ..., source: _Optional[_Union[SourceReference, _Mapping]] = ..., confidence: _Optional[float] = ..., requires_confirmation: _Optional[bool] = ..., review: _Optional[_Union[ReviewState, str]] = ...) -> None: ...

class EntityExtractionResult(_message.Message):
    __slots__ = ("parties", "amounts", "deadlines", "commitments", "penalties", "reference_date", "pipeline_version")
    PARTIES_FIELD_NUMBER: _ClassVar[int]
    AMOUNTS_FIELD_NUMBER: _ClassVar[int]
    DEADLINES_FIELD_NUMBER: _ClassVar[int]
    COMMITMENTS_FIELD_NUMBER: _ClassVar[int]
    PENALTIES_FIELD_NUMBER: _ClassVar[int]
    REFERENCE_DATE_FIELD_NUMBER: _ClassVar[int]
    PIPELINE_VERSION_FIELD_NUMBER: _ClassVar[int]
    parties: _containers.RepeatedCompositeFieldContainer[LegalEntity]
    amounts: _containers.RepeatedCompositeFieldContainer[LegalEntity]
    deadlines: _containers.RepeatedCompositeFieldContainer[LegalEntity]
    commitments: _containers.RepeatedCompositeFieldContainer[LegalEntity]
    penalties: _containers.RepeatedCompositeFieldContainer[LegalEntity]
    reference_date: _values_pb2.CalendarDate
    pipeline_version: str
    def __init__(self, parties: _Optional[_Iterable[_Union[LegalEntity, _Mapping]]] = ..., amounts: _Optional[_Iterable[_Union[LegalEntity, _Mapping]]] = ..., deadlines: _Optional[_Iterable[_Union[LegalEntity, _Mapping]]] = ..., commitments: _Optional[_Iterable[_Union[LegalEntity, _Mapping]]] = ..., penalties: _Optional[_Iterable[_Union[LegalEntity, _Mapping]]] = ..., reference_date: _Optional[_Union[_values_pb2.CalendarDate, _Mapping]] = ..., pipeline_version: _Optional[str] = ...) -> None: ...
