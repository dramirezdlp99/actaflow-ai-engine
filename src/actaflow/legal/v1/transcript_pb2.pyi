from buf.validate import validate_pb2 as _validate_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TranscriptSegment(_message.Message):
    __slots__ = ("speaker_participant_id", "start_ms", "end_ms", "text", "confidence")
    SPEAKER_PARTICIPANT_ID_FIELD_NUMBER: _ClassVar[int]
    START_MS_FIELD_NUMBER: _ClassVar[int]
    END_MS_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    speaker_participant_id: str
    start_ms: int
    end_ms: int
    text: str
    confidence: float
    def __init__(self, speaker_participant_id: _Optional[str] = ..., start_ms: _Optional[int] = ..., end_ms: _Optional[int] = ..., text: _Optional[str] = ..., confidence: _Optional[float] = ...) -> None: ...

class TranscriptionResult(_message.Message):
    __slots__ = ("segments", "language", "model", "audio_duration_ms", "real_time_factor")
    SEGMENTS_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    AUDIO_DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    REAL_TIME_FACTOR_FIELD_NUMBER: _ClassVar[int]
    segments: _containers.RepeatedCompositeFieldContainer[TranscriptSegment]
    language: str
    model: str
    audio_duration_ms: int
    real_time_factor: float
    def __init__(self, segments: _Optional[_Iterable[_Union[TranscriptSegment, _Mapping]]] = ..., language: _Optional[str] = ..., model: _Optional[str] = ..., audio_duration_ms: _Optional[int] = ..., real_time_factor: _Optional[float] = ...) -> None: ...

class HearingTranscript(_message.Message):
    __slots__ = ("segments",)
    SEGMENTS_FIELD_NUMBER: _ClassVar[int]
    segments: _containers.RepeatedCompositeFieldContainer[TranscriptSegment]
    def __init__(self, segments: _Optional[_Iterable[_Union[TranscriptSegment, _Mapping]]] = ...) -> None: ...
