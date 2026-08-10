from __future__ import annotations

import os
import time
from pathlib import Path
from threading import Event

from lazulinet.domain.errors import DependencyMissing, PrivilegeUnavailable, UnsupportedMonitorMode
from lazulinet.domain.models import NetworkObservation, ScanRequest, WirelessInterface, WirelessMode
from lazulinet.ports.interfaces import EventEmitter


def _frequency_to_channel(freq: int) -> int | None:
    if 2412 <= freq <= 2472:
        return (freq - 2407) // 5
    if freq == 2484:
        return 14
    if 5000 <= freq <= 5895:
        return (freq - 5000) // 5
    if 5955 <= freq <= 7115:
        return (freq - 5950) // 5
    return None


def request_wifi_permissions() -> bool:
    """Request Android Wi-Fi discovery permissions when running under python-for-android."""
    if not os.environ.get("ANDROID_ARGUMENT"):
        return False
    try:
        from android.permissions import Permission, request_permissions
        from jnius import autoclass

        sdk = autoclass("android.os.Build$VERSION").SDK_INT
        permissions = [Permission.ACCESS_FINE_LOCATION]
        if sdk >= 33 and hasattr(Permission, "NEARBY_WIFI_DEVICES"):
            permissions.append(Permission.NEARBY_WIFI_DEVICES)
        request_permissions(permissions)
        return True
    except Exception:
        return False


class AndroidWifiAdapter:
    """Safe Android API adapter; no Termux shell or arbitrary command execution."""

    platform_name = "android"

    def __init__(self, wifi_manager_factory=None, wait_cap_seconds: float = 5.0, poll_interval: float = 0.2):
        self._wifi_manager_factory = wifi_manager_factory
        self._wait_cap_seconds = max(0.01, float(wait_cap_seconds))
        self._poll_interval = max(0.01, float(poll_interval))

    def _wifi_manager(self):
        if self._wifi_manager_factory is not None:
            return self._wifi_manager_factory()
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Context = autoclass("android.content.Context")
            activity = PythonActivity.mActivity
            return activity.getApplicationContext().getSystemService(Context.WIFI_SERVICE)
        except Exception as exc:
            raise DependencyMissing(f"Android PyJNIus bridge unavailable: {exc}") from exc

    def list_interfaces(self) -> list[WirelessInterface]:
        wifi = self._wifi_manager()
        enabled = bool(wifi.isWifiEnabled())
        return [WirelessInterface(
            name="android-wifi",
            mode=WirelessMode.MANAGED,
            is_up=enabled,
            supports_monitor=False,
            platform_metadata={"api": "WifiManager"},
        )]

    def set_mode(self, interface: str, mode: WirelessMode) -> WirelessInterface:
        if mode == WirelessMode.MONITOR:
            raise UnsupportedMonitorMode("Packaged Android adapter does not expose monitor mode.")
        return self.list_interfaces()[0]

    def _location_enabled(self) -> bool | None:
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Context = autoclass("android.content.Context")
            BuildVersion = autoclass("android.os.Build$VERSION")
            activity = PythonActivity.mActivity
            manager = activity.getSystemService(Context.LOCATION_SERVICE)
            if BuildVersion.SDK_INT >= 28:
                return bool(manager.isLocationEnabled())
            LocationManager = autoclass("android.location.LocationManager")
            return bool(
                manager.isProviderEnabled(LocationManager.GPS_PROVIDER)
                or manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)
            )
        except Exception:
            return None

    def dependency_status(self) -> dict[str, str]:
        try:
            wifi = self._wifi_manager()
            location = self._location_enabled()
            return {
                "pyjnius": "available",
                "wifi_api": "available",
                "wifi_enabled": "yes" if bool(wifi.isWifiEnabled()) else "no",
                "location_services": "enabled" if location is True else "disabled" if location is False else "unknown",
            }
        except Exception:
            return {
                "pyjnius": "missing",
                "wifi_api": "unavailable",
                "wifi_enabled": "unknown",
                "location_services": "unknown",
            }

    def privilege_status(self) -> str:
        return "android runtime permissions"

    def discover(self, request: ScanRequest, raw_dir: Path, cancel_event: Event, emit: EventEmitter):
        wifi = self._wifi_manager()
        emit("LogLine", "Requesting Android Wi-Fi scan/results", 0.1, None)
        try:
            initiated = bool(wifi.startScan())
        except Exception as exc:
            raise PrivilegeUnavailable(
                "Android Wi-Fi scan permission/location prerequisites are not satisfied."
            ) from exc

        wait_seconds = min(max(float(request.duration_seconds), 0.01), self._wait_cap_seconds)
        started = time.monotonic()
        while time.monotonic() - started < wait_seconds:
            if cancel_event.wait(self._poll_interval):
                return [], []
            progress = 0.1 + 0.6 * ((time.monotonic() - started) / wait_seconds)
            emit("ProgressChanged", "Waiting for Android scan results", min(progress, 0.7), {"scan_initiated": initiated})

        try:
            results = wifi.getScanResults()
        except Exception as exc:
            raise PrivilegeUnavailable(
                "Android scan results are unavailable; check Wi-Fi/location permissions and device settings."
            ) from exc

        observations: list[NetworkObservation] = []
        for result in results:
            if cancel_event.is_set():
                break
            capabilities = str(getattr(result, "capabilities", "") or "")
            frequency = int(getattr(result, "frequency", 0) or 0)
            channel = _frequency_to_channel(frequency)
            if request.channel is not None and channel != request.channel:
                continue
            observations.append(NetworkObservation(
                bssid=str(getattr(result, "BSSID", "") or "").upper(),
                essid=str(getattr(result, "SSID", "") or ""),
                channel=channel,
                privacy=capabilities,
                signal_power=int(getattr(result, "level", 0) or 0),
                platform_metadata={
                    "frequency_mhz": frequency,
                    "android_scan_initiated": initiated,
                },
            ))
        emit("ObservationBatch", f"Android returned {len(observations)} network(s)", 0.9, {"count": len(observations)})
        return observations, []
