from __future__ import annotations

from pathlib import Path
from threading import Event
from typing import Callable, Protocol

from lazulinet.domain.models import NetworkObservation, ScanRequest, WirelessInterface, WirelessMode

EventEmitter = Callable[[str, str, float | None, dict | None], None]


class InterfaceAdapter(Protocol):
    platform_name: str

    def list_interfaces(self) -> list[WirelessInterface]: ...

    def set_mode(self, interface: str, mode: WirelessMode) -> WirelessInterface: ...

    def dependency_status(self) -> dict[str, str]: ...

    def privilege_status(self) -> str: ...


class DiscoveryAdapter(Protocol):
    platform_name: str

    def discover(
        self,
        request: ScanRequest,
        raw_dir: Path,
        cancel_event: Event,
        emit: EventEmitter,
    ) -> tuple[list[NetworkObservation], list[Path]]: ...
