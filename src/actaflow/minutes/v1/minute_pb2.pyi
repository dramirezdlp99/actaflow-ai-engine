import datetime

from actaflow.crypto.v1 import crypto_pb2 as _crypto_pb2
from buf.validate import validate_pb2 as _validate_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class MinuteState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    MINUTE_STATE_UNSPECIFIED: _ClassVar[MinuteState]
    MINUTE_STATE_DRAFT: _ClassVar[MinuteState]
    MINUTE_STATE_SEALING: _ClassVar[MinuteState]
    MINUTE_STATE_AWAITING_ACCEPTANCE: _ClassVar[MinuteState]
    MINUTE_STATE_FINAL: _ClassVar[MinuteState]
MINUTE_STATE_UNSPECIFIED: MinuteState
MINUTE_STATE_DRAFT: MinuteState
MINUTE_STATE_SEALING: MinuteState
MINUTE_STATE_AWAITING_ACCEPTANCE: MinuteState
MINUTE_STATE_FINAL: MinuteState

class Minute(_message.Message):
    __slots__ = ("id", "case_id", "template_id", "template_version", "state", "fill_job_id", "created_at", "closed_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    CASE_ID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_ID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_VERSION_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    FILL_JOB_ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CLOSED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    case_id: str
    template_id: str
    template_version: int
    state: MinuteState
    fill_job_id: str
    created_at: _timestamp_pb2.Timestamp
    closed_at: _timestamp_pb2.Timestamp
    def __init__(self, id: _Optional[str] = ..., case_id: _Optional[str] = ..., template_id: _Optional[str] = ..., template_version: _Optional[int] = ..., state: _Optional[_Union[MinuteState, str]] = ..., fill_job_id: _Optional[str] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., closed_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class CreateMinuteRequest(_message.Message):
    __slots__ = ("case_id", "template_id", "template_version", "idempotency_key")
    CASE_ID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_ID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_VERSION_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    case_id: str
    template_id: str
    template_version: int
    idempotency_key: str
    def __init__(self, case_id: _Optional[str] = ..., template_id: _Optional[str] = ..., template_version: _Optional[int] = ..., idempotency_key: _Optional[str] = ...) -> None: ...

class CreateMinuteResponse(_message.Message):
    __slots__ = ("minute",)
    MINUTE_FIELD_NUMBER: _ClassVar[int]
    minute: Minute
    def __init__(self, minute: _Optional[_Union[Minute, _Mapping]] = ...) -> None: ...

class GetMinuteRequest(_message.Message):
    __slots__ = ("minute_id",)
    MINUTE_ID_FIELD_NUMBER: _ClassVar[int]
    minute_id: str
    def __init__(self, minute_id: _Optional[str] = ...) -> None: ...

class GetMinuteResponse(_message.Message):
    __slots__ = ("minute",)
    MINUTE_FIELD_NUMBER: _ClassVar[int]
    minute: Minute
    def __init__(self, minute: _Optional[_Union[Minute, _Mapping]] = ...) -> None: ...

class ListMinutesRequest(_message.Message):
    __slots__ = ("case_id",)
    CASE_ID_FIELD_NUMBER: _ClassVar[int]
    case_id: str
    def __init__(self, case_id: _Optional[str] = ...) -> None: ...

class ListMinutesResponse(_message.Message):
    __slots__ = ("minutes",)
    MINUTES_FIELD_NUMBER: _ClassVar[int]
    minutes: _containers.RepeatedCompositeFieldContainer[Minute]
    def __init__(self, minutes: _Optional[_Iterable[_Union[Minute, _Mapping]]] = ...) -> None: ...

class FillInput(_message.Message):
    __slots__ = ("reviewed_entities", "case_fields")
    class CaseFieldsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    REVIEWED_ENTITIES_FIELD_NUMBER: _ClassVar[int]
    CASE_FIELDS_FIELD_NUMBER: _ClassVar[int]
    reviewed_entities: bytes
    case_fields: _containers.ScalarMap[str, str]
    def __init__(self, reviewed_entities: _Optional[bytes] = ..., case_fields: _Optional[_Mapping[str, str]] = ...) -> None: ...

class FillMinuteRequest(_message.Message):
    __slots__ = ("minute_id", "input")
    MINUTE_ID_FIELD_NUMBER: _ClassVar[int]
    INPUT_FIELD_NUMBER: _ClassVar[int]
    minute_id: str
    input: _crypto_pb2.SealedEnvelope
    def __init__(self, minute_id: _Optional[str] = ..., input: _Optional[_Union[_crypto_pb2.SealedEnvelope, _Mapping]] = ...) -> None: ...

class FillMinuteResponse(_message.Message):
    __slots__ = ("job_id",)
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    def __init__(self, job_id: _Optional[str] = ...) -> None: ...

class FilledDraft(_message.Message):
    __slots__ = ("html", "missing_variables")
    HTML_FIELD_NUMBER: _ClassVar[int]
    MISSING_VARIABLES_FIELD_NUMBER: _ClassVar[int]
    html: str
    missing_variables: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, html: _Optional[str] = ..., missing_variables: _Optional[_Iterable[str]] = ...) -> None: ...

class CloseMinuteRequest(_message.Message):
    __slots__ = ("minute_id", "final_content", "idempotency_key")
    MINUTE_ID_FIELD_NUMBER: _ClassVar[int]
    FINAL_CONTENT_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    minute_id: str
    final_content: _crypto_pb2.SealedEnvelope
    idempotency_key: str
    def __init__(self, minute_id: _Optional[str] = ..., final_content: _Optional[_Union[_crypto_pb2.SealedEnvelope, _Mapping]] = ..., idempotency_key: _Optional[str] = ...) -> None: ...

class CloseMinuteResponse(_message.Message):
    __slots__ = ("minute", "job_id")
    MINUTE_FIELD_NUMBER: _ClassVar[int]
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    minute: Minute
    job_id: str
    def __init__(self, minute: _Optional[_Union[Minute, _Mapping]] = ..., job_id: _Optional[str] = ...) -> None: ...

class FinalContent(_message.Message):
    __slots__ = ("title", "html")
    TITLE_FIELD_NUMBER: _ClassVar[int]
    HTML_FIELD_NUMBER: _ClassVar[int]
    title: str
    html: str
    def __init__(self, title: _Optional[str] = ..., html: _Optional[str] = ...) -> None: ...

class DocumentSeal(_message.Message):
    __slots__ = ("sha256_hex", "cms_signature", "signer_subject", "certificate_fingerprint_sha256", "sealed_at")
    SHA256_HEX_FIELD_NUMBER: _ClassVar[int]
    CMS_SIGNATURE_FIELD_NUMBER: _ClassVar[int]
    SIGNER_SUBJECT_FIELD_NUMBER: _ClassVar[int]
    CERTIFICATE_FINGERPRINT_SHA256_FIELD_NUMBER: _ClassVar[int]
    SEALED_AT_FIELD_NUMBER: _ClassVar[int]
    sha256_hex: str
    cms_signature: bytes
    signer_subject: str
    certificate_fingerprint_sha256: str
    sealed_at: _timestamp_pb2.Timestamp
    def __init__(self, sha256_hex: _Optional[str] = ..., cms_signature: _Optional[bytes] = ..., signer_subject: _Optional[str] = ..., certificate_fingerprint_sha256: _Optional[str] = ..., sealed_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class Acceptance(_message.Message):
    __slots__ = ("participant_id", "display_name", "accepted_at")
    PARTICIPANT_ID_FIELD_NUMBER: _ClassVar[int]
    DISPLAY_NAME_FIELD_NUMBER: _ClassVar[int]
    ACCEPTED_AT_FIELD_NUMBER: _ClassVar[int]
    participant_id: str
    display_name: str
    accepted_at: _timestamp_pb2.Timestamp
    def __init__(self, participant_id: _Optional[str] = ..., display_name: _Optional[str] = ..., accepted_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class FinalDocument(_message.Message):
    __slots__ = ("id", "minute_id", "pdf", "content_key_for_case", "seal", "acceptances", "pending_participant_ids")
    ID_FIELD_NUMBER: _ClassVar[int]
    MINUTE_ID_FIELD_NUMBER: _ClassVar[int]
    PDF_FIELD_NUMBER: _ClassVar[int]
    CONTENT_KEY_FOR_CASE_FIELD_NUMBER: _ClassVar[int]
    SEAL_FIELD_NUMBER: _ClassVar[int]
    ACCEPTANCES_FIELD_NUMBER: _ClassVar[int]
    PENDING_PARTICIPANT_IDS_FIELD_NUMBER: _ClassVar[int]
    id: str
    minute_id: str
    pdf: _crypto_pb2.EncryptedBlob
    content_key_for_case: _crypto_pb2.EncryptedBlob
    seal: DocumentSeal
    acceptances: _containers.RepeatedCompositeFieldContainer[Acceptance]
    pending_participant_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, id: _Optional[str] = ..., minute_id: _Optional[str] = ..., pdf: _Optional[_Union[_crypto_pb2.EncryptedBlob, _Mapping]] = ..., content_key_for_case: _Optional[_Union[_crypto_pb2.EncryptedBlob, _Mapping]] = ..., seal: _Optional[_Union[DocumentSeal, _Mapping]] = ..., acceptances: _Optional[_Iterable[_Union[Acceptance, _Mapping]]] = ..., pending_participant_ids: _Optional[_Iterable[str]] = ...) -> None: ...

class GetFinalDocumentRequest(_message.Message):
    __slots__ = ("minute_id",)
    MINUTE_ID_FIELD_NUMBER: _ClassVar[int]
    minute_id: str
    def __init__(self, minute_id: _Optional[str] = ...) -> None: ...

class GetFinalDocumentResponse(_message.Message):
    __slots__ = ("document",)
    DOCUMENT_FIELD_NUMBER: _ClassVar[int]
    document: FinalDocument
    def __init__(self, document: _Optional[_Union[FinalDocument, _Mapping]] = ...) -> None: ...

class AcceptFinalDocumentRequest(_message.Message):
    __slots__ = ("document_id", "sha256_hex", "totp_code", "presence_token")
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SHA256_HEX_FIELD_NUMBER: _ClassVar[int]
    TOTP_CODE_FIELD_NUMBER: _ClassVar[int]
    PRESENCE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    sha256_hex: str
    totp_code: str
    presence_token: str
    def __init__(self, document_id: _Optional[str] = ..., sha256_hex: _Optional[str] = ..., totp_code: _Optional[str] = ..., presence_token: _Optional[str] = ...) -> None: ...

class AcceptFinalDocumentResponse(_message.Message):
    __slots__ = ("document",)
    DOCUMENT_FIELD_NUMBER: _ClassVar[int]
    document: FinalDocument
    def __init__(self, document: _Optional[_Union[FinalDocument, _Mapping]] = ...) -> None: ...

class VerifyDocumentRequest(_message.Message):
    __slots__ = ("sha256_hex",)
    SHA256_HEX_FIELD_NUMBER: _ClassVar[int]
    sha256_hex: str
    def __init__(self, sha256_hex: _Optional[str] = ...) -> None: ...

class VerifyDocumentResponse(_message.Message):
    __slots__ = ("authentic", "seal", "organization_name", "case_number", "acceptance_count")
    AUTHENTIC_FIELD_NUMBER: _ClassVar[int]
    SEAL_FIELD_NUMBER: _ClassVar[int]
    ORGANIZATION_NAME_FIELD_NUMBER: _ClassVar[int]
    CASE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    ACCEPTANCE_COUNT_FIELD_NUMBER: _ClassVar[int]
    authentic: bool
    seal: DocumentSeal
    organization_name: str
    case_number: str
    acceptance_count: int
    def __init__(self, authentic: _Optional[bool] = ..., seal: _Optional[_Union[DocumentSeal, _Mapping]] = ..., organization_name: _Optional[str] = ..., case_number: _Optional[str] = ..., acceptance_count: _Optional[int] = ...) -> None: ...
