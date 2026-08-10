from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class WirelessInterface:
    name: str
    mode: str = "unknown"
    is_up: bool = False
    mac_address: str = ""
    supports_monitor: bool | None = None


@dataclass
class NetworkObservation:
    bssid: str = ""
    essid: str = ""
    channel: str = ""
    privacy: str = ""
    cipher: str = ""
    auth: str = ""
    signal_power: str = ""
    clients: list[str] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "NetworkObservation":
        return cls(
            bssid=str(data.get("bssid", data.get("BSSID", ""))),
            essid=str(data.get("essid", data.get("ESSID", ""))),
            channel=str(data.get("channel", data.get("Channel", ""))),
            privacy=str(data.get("privacy", data.get("Privacy", ""))),
            cipher=str(data.get("cipher", data.get("Cipher", ""))),
            auth=str(data.get("auth", data.get("Authentication", data.get("Auth", "")))),
            signal_power=str(data.get("signal_power", data.get("power", data.get("Power", "")))),
            clients=[str(x) for x in data.get("clients", []) if x],
        )


@dataclass
class AppStatus:
    platform: str
    privilege: str
    active_interface: str
    interface_mode: str
    network_count: int
    storage_path: str
    updated_at: datetime = field(default_factory=datetime.now)
