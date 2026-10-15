from buf.validate import validate_pb2 as _validate_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CipherSuite(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CIPHER_SUITE_UNSPECIFIED: _ClassVar[CipherSuite]
    CIPHER_SUITE_AES_256_GCM: _ClassVar[CipherSuite]
    CIPHER_SUITE_ECDH_P256_HKDF_SHA256_AES_256_GCM: _ClassVar[CipherSuite]

class ProcessorKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PROCESSOR_KIND_UNSPECIFIED: _ClassVar[ProcessorKind]
    PROCESSOR_KIND_AI_ENGINE: _ClassVar[ProcessorKind]
    PROCESSOR_KIND_DOCUMENT_WORKER: _ClassVar[ProcessorKind]
CIPHER_SUITE_UNSPECIFIED: CipherSuite
CIPHER_SUITE_AES_256_GCM: CipherSuite
CIPHER_SUITE_ECDH_P256_HKDF_SHA256_AES_256_GCM: CipherSuite
PROCESSOR_KIND_UNSPECIFIED: ProcessorKind
PROCESSOR_KIND_AI_ENGINE: ProcessorKind
PROCESSOR_KIND_DOCUMENT_WORKER: ProcessorKind

class EncryptedBlob(_message.Message):
    __slots__ = ("suite", "key_id", "nonce", "ciphertext", "plaintext_type")
    SUITE_FIELD_NUMBER: _ClassVar[int]
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    NONCE_FIELD_NUMBER: _ClassVar[int]
    CIPHERTEXT_FIELD_NUMBER: _ClassVar[int]
    PLAINTEXT_TYPE_FIELD_NUMBER: _ClassVar[int]
    suite: CipherSuite
    key_id: str
    nonce: bytes
    ciphertext: bytes
    plaintext_type: str
    def __init__(self, suite: _Optional[_Union[CipherSuite, str]] = ..., key_id: _Optional[str] = ..., nonce: _Optional[bytes] = ..., ciphertext: _Optional[bytes] = ..., plaintext_type: _Optional[str] = ...) -> None: ...

class WrappedKey(_message.Message):
    __slots__ = ("suite", "recipient_key_id", "ephemeral_public_key", "nonce", "wrapped_key")
    SUITE_FIELD_NUMBER: _ClassVar[int]
    RECIPIENT_KEY_ID_FIELD_NUMBER: _ClassVar[int]
    EPHEMERAL_PUBLIC_KEY_FIELD_NUMBER: _ClassVar[int]
    NONCE_FIELD_NUMBER: _ClassVar[int]
    WRAPPED_KEY_FIELD_NUMBER: _ClassVar[int]
    suite: CipherSuite
    recipient_key_id: str
    ephemeral_public_key: bytes
    nonce: bytes
    wrapped_key: bytes
    def __init__(self, suite: _Optional[_Union[CipherSuite, str]] = ..., recipient_key_id: _Optional[str] = ..., ephemeral_public_key: _Optional[bytes] = ..., nonce: _Optional[bytes] = ..., wrapped_key: _Optional[bytes] = ...) -> None: ...

class SealedEnvelope(_message.Message):
    __slots__ = ("payload", "processor_key", "content_key_for_case")
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    PROCESSOR_KEY_FIELD_NUMBER: _ClassVar[int]
    CONTENT_KEY_FOR_CASE_FIELD_NUMBER: _ClassVar[int]
    payload: EncryptedBlob
    processor_key: WrappedKey
    content_key_for_case: EncryptedBlob
    def __init__(self, payload: _Optional[_Union[EncryptedBlob, _Mapping]] = ..., processor_key: _Optional[_Union[WrappedKey, _Mapping]] = ..., content_key_for_case: _Optional[_Union[EncryptedBlob, _Mapping]] = ...) -> None: ...

class PublicKey(_message.Message):
    __slots__ = ("key_id", "algorithm", "public_key", "fingerprint_sha256")
    KEY_ID_FIELD_NUMBER: _ClassVar[int]
    ALGORITHM_FIELD_NUMBER: _ClassVar[int]
    PUBLIC_KEY_FIELD_NUMBER: _ClassVar[int]
    FINGERPRINT_SHA256_FIELD_NUMBER: _ClassVar[int]
    key_id: str
    algorithm: str
    public_key: bytes
    fingerprint_sha256: str
    def __init__(self, key_id: _Optional[str] = ..., algorithm: _Optional[str] = ..., public_key: _Optional[bytes] = ..., fingerprint_sha256: _Optional[str] = ...) -> None: ...

class ProcessorKey(_message.Message):
    __slots__ = ("kind", "key")
    KIND_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    kind: ProcessorKind
    key: PublicKey
    def __init__(self, kind: _Optional[_Union[ProcessorKind, str]] = ..., key: _Optional[_Union[PublicKey, _Mapping]] = ...) -> None: ...

class GetProcessorKeysRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetProcessorKeysResponse(_message.Message):
    __slots__ = ("keys",)
    KEYS_FIELD_NUMBER: _ClassVar[int]
    keys: _containers.RepeatedCompositeFieldContainer[ProcessorKey]
    def __init__(self, keys: _Optional[_Iterable[_Union[ProcessorKey, _Mapping]]] = ...) -> None: ...
