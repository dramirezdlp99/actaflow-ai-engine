from buf.validate import validate_pb2 as _validate_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class Money(_message.Message):
    __slots__ = ("currency_code", "units", "nanos")
    CURRENCY_CODE_FIELD_NUMBER: _ClassVar[int]
    UNITS_FIELD_NUMBER: _ClassVar[int]
    NANOS_FIELD_NUMBER: _ClassVar[int]
    currency_code: str
    units: int
    nanos: int
    def __init__(self, currency_code: _Optional[str] = ..., units: _Optional[int] = ..., nanos: _Optional[int] = ...) -> None: ...

class CalendarDate(_message.Message):
    __slots__ = ("year", "month", "day")
    YEAR_FIELD_NUMBER: _ClassVar[int]
    MONTH_FIELD_NUMBER: _ClassVar[int]
    DAY_FIELD_NUMBER: _ClassVar[int]
    year: int
    month: int
    day: int
    def __init__(self, year: _Optional[int] = ..., month: _Optional[int] = ..., day: _Optional[int] = ...) -> None: ...

class TextSpan(_message.Message):
    __slots__ = ("start", "end")
    START_FIELD_NUMBER: _ClassVar[int]
    END_FIELD_NUMBER: _ClassVar[int]
    start: int
    end: int
    def __init__(self, start: _Optional[int] = ..., end: _Optional[int] = ...) -> None: ...
