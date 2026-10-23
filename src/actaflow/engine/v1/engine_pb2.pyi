from actaflow.common.v1 import values_pb2 as _values_pb2
from actaflow.crypto.v1 import crypto_pb2 as _crypto_pb2
from buf.validate import validate_pb2 as _validate_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AudioEncoding(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AUDIO_ENCODING_UNSPECIFIED: _ClassVar[AudioEncoding]
    AUDIO_ENCODING_OGG_OPUS: _ClassVar[AudioEncoding]
    AUDIO_ENCODING_WAV_PCM16: _ClassVar[AudioEncoding]

class ModelSize(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    MODEL_SIZE_UNSPECIFIED: _ClassVar[ModelSize]
    MODEL_SIZE_TINY: _ClassVar[ModelSize]
    MODEL_SIZE_BASE: _ClassVar[ModelSize]
    MODEL_SIZE_SMALL: _ClassVar[ModelSize]

class BenchmarkOutcome(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    BENCHMARK_OUTCOME_UNSPECIFIED: _ClassVar[BenchmarkOutcome]
    BENCHMARK_OUTCOME_OK: _ClassVar[BenchmarkOutcome]
    BENCHMARK_OUTCOME_OUT_OF_MEMORY: _ClassVar[BenchmarkOutcome]
    BENCHMARK_OUTCOME_TIMEOUT: _ClassVar[BenchmarkOutcome]
    BENCHMARK_OUTCOME_ERROR: _ClassVar[BenchmarkOutcome]
    BENCHMARK_OUTCOME_NOT_INSTALLED: _ClassVar[BenchmarkOutcome]
AUDIO_ENCODING_UNSPECIFIED: AudioEncoding
AUDIO_ENCODING_OGG_OPUS: AudioEncoding
AUDIO_ENCODING_WAV_PCM16: AudioEncoding
MODEL_SIZE_UNSPECIFIED: ModelSize
MODEL_SIZE_TINY: ModelSize
MODEL_SIZE_BASE: ModelSize
MODEL_SIZE_SMALL: ModelSize
BENCHMARK_OUTCOME_UNSPECIFIED: BenchmarkOutcome
BENCHMARK_OUTCOME_OK: BenchmarkOutcome
BENCHMARK_OUTCOME_OUT_OF_MEMORY: BenchmarkOutcome
BENCHMARK_OUTCOME_TIMEOUT: BenchmarkOutcome
BENCHMARK_OUTCOME_ERROR: BenchmarkOutcome
BENCHMARK_OUTCOME_NOT_INSTALLED: BenchmarkOutcome

class RecognitionHints(_message.Message):
    __slots__ = ("names", "vocabulary")
    NAMES_FIELD_NUMBER: _ClassVar[int]
    VOCABULARY_FIELD_NUMBER: _ClassVar[int]
    names: _containers.RepeatedScalarFieldContainer[str]
    vocabulary: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, names: _Optional[_Iterable[str]] = ..., vocabulary: _Optional[_Iterable[str]] = ...) -> None: ...

class SealedAudioSegment(_message.Message):
    __slots__ = ("audio", "encoding", "speaker_participant_id", "hints")
    AUDIO_FIELD_NUMBER: _ClassVar[int]
    ENCODING_FIELD_NUMBER: _ClassVar[int]
    SPEAKER_PARTICIPANT_ID_FIELD_NUMBER: _ClassVar[int]
    HINTS_FIELD_NUMBER: _ClassVar[int]
    audio: bytes
    encoding: AudioEncoding
    speaker_participant_id: str
    hints: RecognitionHints
    def __init__(self, audio: _Optional[bytes] = ..., encoding: _Optional[_Union[AudioEncoding, str]] = ..., speaker_participant_id: _Optional[str] = ..., hints: _Optional[_Union[RecognitionHints, _Mapping]] = ...) -> None: ...

class TranscribeSegmentRequest(_message.Message):
    __slots__ = ("case_id", "segment_id", "audio", "language")
    CASE_ID_FIELD_NUMBER: _ClassVar[int]
    SEGMENT_ID_FIELD_NUMBER: _ClassVar[int]
    AUDIO_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    case_id: str
    segment_id: str
    audio: _crypto_pb2.SealedEnvelope
    language: str
    def __init__(self, case_id: _Optional[str] = ..., segment_id: _Optional[str] = ..., audio: _Optional[_Union[_crypto_pb2.SealedEnvelope, _Mapping]] = ..., language: _Optional[str] = ...) -> None: ...

class TranscribeSegmentResponse(_message.Message):
    __slots__ = ("transcript",)
    TRANSCRIPT_FIELD_NUMBER: _ClassVar[int]
    transcript: _crypto_pb2.EncryptedBlob
    def __init__(self, transcript: _Optional[_Union[_crypto_pb2.EncryptedBlob, _Mapping]] = ...) -> None: ...

class StreamTranscriptionRequest(_message.Message):
    __slots__ = ("start", "chunk")
    START_FIELD_NUMBER: _ClassVar[int]
    CHUNK_FIELD_NUMBER: _ClassVar[int]
    start: StreamTranscriptionStart
    chunk: _crypto_pb2.EncryptedBlob
    def __init__(self, start: _Optional[_Union[StreamTranscriptionStart, _Mapping]] = ..., chunk: _Optional[_Union[_crypto_pb2.EncryptedBlob, _Mapping]] = ...) -> None: ...

class StreamTranscriptionStart(_message.Message):
    __slots__ = ("case_id", "session_id", "content_key", "encoding")
    CASE_ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    CONTENT_KEY_FIELD_NUMBER: _ClassVar[int]
    ENCODING_FIELD_NUMBER: _ClassVar[int]
    case_id: str
    session_id: str
    content_key: _crypto_pb2.WrappedKey
    encoding: AudioEncoding
    def __init__(self, case_id: _Optional[str] = ..., session_id: _Optional[str] = ..., content_key: _Optional[_Union[_crypto_pb2.WrappedKey, _Mapping]] = ..., encoding: _Optional[_Union[AudioEncoding, str]] = ...) -> None: ...

class StreamTranscriptionResponse(_message.Message):
    __slots__ = ("partial", "final")
    PARTIAL_FIELD_NUMBER: _ClassVar[int]
    FINAL_FIELD_NUMBER: _ClassVar[int]
    partial: _crypto_pb2.EncryptedBlob
    final: bool
    def __init__(self, partial: _Optional[_Union[_crypto_pb2.EncryptedBlob, _Mapping]] = ..., final: _Optional[bool] = ...) -> None: ...

class RenderMinutePdfRequest(_message.Message):
    __slots__ = ("case_id", "minute_id", "final_content")
    CASE_ID_FIELD_NUMBER: _ClassVar[int]
    MINUTE_ID_FIELD_NUMBER: _ClassVar[int]
    FINAL_CONTENT_FIELD_NUMBER: _ClassVar[int]
    case_id: str
    minute_id: str
    final_content: _crypto_pb2.SealedEnvelope
    def __init__(self, case_id: _Optional[str] = ..., minute_id: _Optional[str] = ..., final_content: _Optional[_Union[_crypto_pb2.SealedEnvelope, _Mapping]] = ...) -> None: ...

class RenderMinutePdfResponse(_message.Message):
    __slots__ = ("pdf", "sha256_hex", "page_count")
    PDF_FIELD_NUMBER: _ClassVar[int]
    SHA256_HEX_FIELD_NUMBER: _ClassVar[int]
    PAGE_COUNT_FIELD_NUMBER: _ClassVar[int]
    pdf: _crypto_pb2.EncryptedBlob
    sha256_hex: str
    page_count: int
    def __init__(self, pdf: _Optional[_Union[_crypto_pb2.EncryptedBlob, _Mapping]] = ..., sha256_hex: _Optional[str] = ..., page_count: _Optional[int] = ...) -> None: ...

class ExtractionInput(_message.Message):
    __slots__ = ("text", "reference_date", "participants")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    REFERENCE_DATE_FIELD_NUMBER: _ClassVar[int]
    PARTICIPANTS_FIELD_NUMBER: _ClassVar[int]
    text: str
    reference_date: _values_pb2.CalendarDate
    participants: _containers.RepeatedCompositeFieldContainer[KnownParticipant]
    def __init__(self, text: _Optional[str] = ..., reference_date: _Optional[_Union[_values_pb2.CalendarDate, _Mapping]] = ..., participants: _Optional[_Iterable[_Union[KnownParticipant, _Mapping]]] = ...) -> None: ...

class KnownParticipant(_message.Message):
    __slots__ = ("participant_id", "display_name")
    PARTICIPANT_ID_FIELD_NUMBER: _ClassVar[int]
    DISPLAY_NAME_FIELD_NUMBER: _ClassVar[int]
    participant_id: str
    display_name: str
    def __init__(self, participant_id: _Optional[str] = ..., display_name: _Optional[str] = ...) -> None: ...

class ExtractEntitiesRequest(_message.Message):
    __slots__ = ("case_id", "extraction_id", "input")
    CASE_ID_FIELD_NUMBER: _ClassVar[int]
    EXTRACTION_ID_FIELD_NUMBER: _ClassVar[int]
    INPUT_FIELD_NUMBER: _ClassVar[int]
    case_id: str
    extraction_id: str
    input: _crypto_pb2.SealedEnvelope
    def __init__(self, case_id: _Optional[str] = ..., extraction_id: _Optional[str] = ..., input: _Optional[_Union[_crypto_pb2.SealedEnvelope, _Mapping]] = ...) -> None: ...

class ExtractEntitiesResponse(_message.Message):
    __slots__ = ("entities",)
    ENTITIES_FIELD_NUMBER: _ClassVar[int]
    entities: _crypto_pb2.EncryptedBlob
    def __init__(self, entities: _Optional[_Union[_crypto_pb2.EncryptedBlob, _Mapping]] = ...) -> None: ...

class RunBenchmarkRequest(_message.Message):
    __slots__ = ("models", "include_nlp")
    MODELS_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_NLP_FIELD_NUMBER: _ClassVar[int]
    models: _containers.RepeatedScalarFieldContainer[ModelSize]
    include_nlp: bool
    def __init__(self, models: _Optional[_Iterable[_Union[ModelSize, str]]] = ..., include_nlp: _Optional[bool] = ...) -> None: ...

class ContainerLimits(_message.Message):
    __slots__ = ("memory_limit_bytes", "cpu_quota_cores", "visible_cpus")
    MEMORY_LIMIT_BYTES_FIELD_NUMBER: _ClassVar[int]
    CPU_QUOTA_CORES_FIELD_NUMBER: _ClassVar[int]
    VISIBLE_CPUS_FIELD_NUMBER: _ClassVar[int]
    memory_limit_bytes: int
    cpu_quota_cores: float
    visible_cpus: int
    def __init__(self, memory_limit_bytes: _Optional[int] = ..., cpu_quota_cores: _Optional[float] = ..., visible_cpus: _Optional[int] = ...) -> None: ...

class ModelBenchmark(_message.Message):
    __slots__ = ("model", "outcome", "detail", "load_seconds", "transcription_seconds", "audio_seconds", "real_time_factor", "peak_memory_bytes", "word_error_rate", "text")
    MODEL_FIELD_NUMBER: _ClassVar[int]
    OUTCOME_FIELD_NUMBER: _ClassVar[int]
    DETAIL_FIELD_NUMBER: _ClassVar[int]
    LOAD_SECONDS_FIELD_NUMBER: _ClassVar[int]
    TRANSCRIPTION_SECONDS_FIELD_NUMBER: _ClassVar[int]
    AUDIO_SECONDS_FIELD_NUMBER: _ClassVar[int]
    REAL_TIME_FACTOR_FIELD_NUMBER: _ClassVar[int]
    PEAK_MEMORY_BYTES_FIELD_NUMBER: _ClassVar[int]
    WORD_ERROR_RATE_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    model: ModelSize
    outcome: BenchmarkOutcome
    detail: str
    load_seconds: float
    transcription_seconds: float
    audio_seconds: float
    real_time_factor: float
    peak_memory_bytes: int
    word_error_rate: float
    text: str
    def __init__(self, model: _Optional[_Union[ModelSize, str]] = ..., outcome: _Optional[_Union[BenchmarkOutcome, str]] = ..., detail: _Optional[str] = ..., load_seconds: _Optional[float] = ..., transcription_seconds: _Optional[float] = ..., audio_seconds: _Optional[float] = ..., real_time_factor: _Optional[float] = ..., peak_memory_bytes: _Optional[int] = ..., word_error_rate: _Optional[float] = ..., text: _Optional[str] = ...) -> None: ...

class RunBenchmarkResponse(_message.Message):
    __slots__ = ("limits", "results")
    LIMITS_FIELD_NUMBER: _ClassVar[int]
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    limits: ContainerLimits
    results: _containers.RepeatedCompositeFieldContainer[ModelBenchmark]
    def __init__(self, limits: _Optional[_Union[ContainerLimits, _Mapping]] = ..., results: _Optional[_Iterable[_Union[ModelBenchmark, _Mapping]]] = ...) -> None: ...
