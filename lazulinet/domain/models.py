from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class WirelessMode(str, Enum):
    MANAGED = "managed"
    MONITOR = "monitor"
    UNKNOWN = "unknown"


class SessionStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TaskState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class WirelessInterface:
    name: str
    mac_address: str = ""
    mode: WirelessMode = WirelessMode.UNKNOWN
    is_up: bool = False
    supports_monitor: bool | None = None
    platform_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["mode"] = self.mode.value
        return data


@dataclass(slots=True)
class NetworkObservation:
    bssid: str
    essid: str = ""
    channel: int | None = None
    privacy: str = ""
    cipher: str = ""
    auth: str = ""
    signal_power: int | None = None
    beacons: int | None = None
    data_frames: int | None = None
    clients: list[str] = field(default_factory=list)
    first_seen: str = ""
    last_seen: str = ""
    platform_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NetworkObservation":
        allowed = {name for name in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in allowed})


@dataclass(slots=True)
class ScanRequest:
    interface: str
    duration_seconds: int = 30
    channel: int | None = None


@dataclass(slots=True)
class ScanSession:
    id: str
    platform: str
    interface: str
    started_at: str
    status: SessionStatus = SessionStatus.CREATED
    ended_at: str = ""
    channel_filter: int | None = None
    network_count: int = 0
    error: str = ""
    raw_artifacts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScanSession":
        copy = dict(data)
        copy["status"] = SessionStatus(copy.get("status", SessionStatus.CREATED.value))
        return cls(**copy)


@dataclass(slots=True)
class TaskEvent:
    task_id: str
    kind: str
    message: str
    timestamp: str = field(default_factory=utc_now_iso)
    progress: float | None = None
    payload: dict[str, Any] = field(default_factory=dict)
