from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from lazulinet.domain.errors import DependencyMissing, InterfaceNotFound, PrivilegeUnavailable, ProcessFailed, UnsupportedMonitorMode
from lazulinet.domain.models import WirelessInterface, WirelessMode
from lazulinet.domain.validation import validate_interface_name


class DebianInterfaceAdapter:
    platform_name = "debian"

    def __init__(self, runner=None):
        self._runner = runner or subprocess.run

    def _require(self, binary: str) -> str:
        path = shutil.which(binary)
        if not path:
            raise DependencyMissing(f"Required dependency is missing: {binary}")
        return path

    def _privileged(self, argv: list[str]) -> list[str]:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            return argv
        sudo = shutil.which("sudo")
        if not sudo:
            raise PrivilegeUnavailable("Root privilege is required and sudo is unavailable.")
        return [sudo, "-n", *argv]

    def _run_checked(self, argv: list[str], timeout: int = 8) -> subprocess.CompletedProcess:
        result = self._runner(argv, text=True, capture_output=True, timeout=timeout, check=False)
        if result.returncode != 0:
            stderr = (result.stderr or result.stdout or "").strip()
            raise ProcessFailed(f"Command failed ({result.returncode}): {stderr or argv[0]}")
        return result

    @staticmethod
    def parse_iw_dev(text: str) -> list[WirelessInterface]:
        interfaces: list[WirelessInterface] = []
        current: WirelessInterface | None = None
        for raw in text.splitlines():
            line = raw.strip()
            if line.startswith("Interface "):
                current = WirelessInterface(name=line.split(maxsplit=1)[1])
                interfaces.append(current)
            elif current and line.startswith("addr "):
                current.mac_address = line.split(maxsplit=1)[1]
            elif current and line.startswith("type "):
                value = line.split(maxsplit=1)[1].lower()
                current.mode = WirelessMode.MONITOR if value == "monitor" else WirelessMode.MANAGED if value == "managed" else WirelessMode.UNKNOWN
                current.supports_monitor = True
            elif current and line.startswith("channel "):
                current.platform_metadata["channel"] = line.split()[1]
        return interfaces

    def list_interfaces(self) -> list[WirelessInterface]:
        interfaces: list[WirelessInterface] = []
        iw = shutil.which("iw")
        if iw:
            result = self._runner([iw, "dev"], text=True, capture_output=True, timeout=5, check=False)
            if result.returncode == 0:
                interfaces = self.parse_iw_dev(result.stdout)

        by_name = {i.name: i for i in interfaces}
        sys_net = Path("/sys/class/net")
        if sys_net.exists():
            for item in sorted(sys_net.iterdir()):
                if item.name == "lo":
                    continue
                iface = by_name.get(item.name) or WirelessInterface(name=item.name)
                try:
                    iface.mac_address = (item / "address").read_text().strip()
                except OSError:
                    pass
                try:
                    iface.is_up = (item / "operstate").read_text().strip() == "up"
                except OSError:
                    pass
                if (item / "wireless").exists() and iface.supports_monitor is None:
                    iface.supports_monitor = True
                by_name[item.name] = iface
        return list(by_name.values())

    def get_interface(self, name: str) -> WirelessInterface:
        name = validate_interface_name(name)
        for iface in self.list_interfaces():
            if iface.name == name:
                return iface
        raise InterfaceNotFound(name)

    def set_mode(self, interface: str, mode: WirelessMode) -> WirelessInterface:
        interface = validate_interface_name(interface)
        current = self.get_interface(interface)
        if current.supports_monitor is False and mode == WirelessMode.MONITOR:
            raise UnsupportedMonitorMode(interface)
        if mode not in (WirelessMode.MANAGED, WirelessMode.MONITOR):
            raise UnsupportedMonitorMode(f"Unsupported requested mode: {mode}")
        ip = self._require("ip")
        iw = self._require("iw")
        try:
            self._run_checked(self._privileged([ip, "link", "set", interface, "down"]))
            self._run_checked(self._privileged([iw, "dev", interface, "set", "type", mode.value]))
        finally:
            try:
                self._run_checked(self._privileged([ip, "link", "set", interface, "up"]))
            except Exception:
                pass
        return self.get_interface(interface)

    def dependency_status(self) -> dict[str, str]:
        names = ["iw", "ip", "airodump-ng"]
        if not (hasattr(os, "geteuid") and os.geteuid() == 0):
            names.append("sudo")
        return {name: ("available" if shutil.which(name) else "missing") for name in names}

    def privilege_status(self) -> str:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            return "root"
        if shutil.which("sudo"):
            probe = self._runner(["sudo", "-n", "true"], text=True, capture_output=True, timeout=3, check=False)
            return "sudo ready" if probe.returncode == 0 else "sudo authentication required"
        return "unprivileged"
