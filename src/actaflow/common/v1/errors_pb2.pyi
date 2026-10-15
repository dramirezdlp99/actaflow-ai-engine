from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ErrorReason(_message.Message):
    __slots__ = ("reason", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    REASON_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    reason: str
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, reason: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...

class FieldViolation(_message.Message):
    __slots__ = ("field", "rule", "description")
    FIELD_FIELD_NUMBER: _ClassVar[int]
    RULE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    field: str
    rule: str
    description: str
    def __init__(self, field: _Optional[str] = ..., rule: _Optional[str] = ..., description: _Optional[str] = ...) -> None: ...

class FieldViolations(_message.Message):
    __slots__ = ("violations",)
    VIOLATIONS_FIELD_NUMBER: _ClassVar[int]
    violations: _containers.RepeatedCompositeFieldContainer[FieldViolation]
    def __init__(self, violations: _Optional[_Iterable[_Union[FieldViolation, _Mapping]]] = ...) -> None: ...

class RetryAfter(_message.Message):
    __slots__ = ("seconds",)
    SECONDS_FIELD_NUMBER: _ClassVar[int]
    seconds: int
    def __init__(self, seconds: _Optional[int] = ...) -> None: ...
