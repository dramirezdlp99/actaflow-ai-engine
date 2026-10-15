import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class HealthState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    HEALTH_STATE_UNSPECIFIED: _ClassVar[HealthState]
    HEALTH_STATE_OK: _ClassVar[HealthState]
    HEALTH_STATE_DEGRADED: _ClassVar[HealthState]
    HEALTH_STATE_DOWN: _ClassVar[HealthState]

class ComponentKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    COMPONENT_KIND_UNSPECIFIED: _ClassVar[ComponentKind]
    COMPONENT_KIND_DATABASE: _ClassVar[ComponentKind]
    COMPONENT_KIND_SERVICE: _ClassVar[ComponentKind]
    COMPONENT_KIND_MODEL: _ClassVar[ComponentKind]

class Transport(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TRANSPORT_UNSPECIFIED: _ClassVar[Transport]
    TRANSPORT_GRPC: _ClassVar[Transport]
    TRANSPORT_GRPC_WEB: _ClassVar[Transport]
HEALTH_STATE_UNSPECIFIED: HealthState
HEALTH_STATE_OK: HealthState
HEALTH_STATE_DEGRADED: HealthState
HEALTH_STATE_DOWN: HealthState
COMPONENT_KIND_UNSPECIFIED: ComponentKind
COMPONENT_KIND_DATABASE: ComponentKind
COMPONENT_KIND_SERVICE: ComponentKind
COMPONENT_KIND_MODEL: ComponentKind
TRANSPORT_UNSPECIFIED: Transport
TRANSPORT_GRPC: Transport
TRANSPORT_GRPC_WEB: Transport

class GetServiceStatusRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetServiceStatusResponse(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: ServiceStatus
    def __init__(self, status: _Optional[_Union[ServiceStatus, _Mapping]] = ...) -> None: ...

class ServiceStatus(_message.Message):
    __slots__ = ("service_name", "version", "state", "checked_at", "served_via", "components")
    SERVICE_NAME_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    CHECKED_AT_FIELD_NUMBER: _ClassVar[int]
    SERVED_VIA_FIELD_NUMBER: _ClassVar[int]
    COMPONENTS_FIELD_NUMBER: _ClassVar[int]
    service_name: str
    version: str
    state: HealthState
    checked_at: _timestamp_pb2.Timestamp
    served_via: Transport
    components: _containers.RepeatedCompositeFieldContainer[ComponentStatus]
    def __init__(self, service_name: _Optional[str] = ..., version: _Optional[str] = ..., state: _Optional[_Union[HealthState, str]] = ..., checked_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., served_via: _Optional[_Union[Transport, str]] = ..., components: _Optional[_Iterable[_Union[ComponentStatus, _Mapping]]] = ...) -> None: ...

class ComponentStatus(_message.Message):
    __slots__ = ("id", "kind", "state", "latency_ms", "detail", "version", "nested")
    ID_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    LATENCY_MS_FIELD_NUMBER: _ClassVar[int]
    DETAIL_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    NESTED_FIELD_NUMBER: _ClassVar[int]
    id: str
    kind: ComponentKind
    state: HealthState
    latency_ms: int
    detail: str
    version: str
    nested: ServiceStatus
    def __init__(self, id: _Optional[str] = ..., kind: _Optional[_Union[ComponentKind, str]] = ..., state: _Optional[_Union[HealthState, str]] = ..., latency_ms: _Optional[int] = ..., detail: _Optional[str] = ..., version: _Optional[str] = ..., nested: _Optional[_Union[ServiceStatus, _Mapping]] = ...) -> None: ...
