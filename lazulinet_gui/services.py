from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Callable

from .models import NetworkObservation, WirelessInterface


class RepositoryBridge:
    """
    Safe GUI-side bridge.

    v0.1 intentionally provides:
      - interface inspection
      - dependency checks
      - networks.json import
      - session discovery
      - report generation

    It deliberately does not invoke legacy attack/crack/evil-twin operations.
    Discovery execution should be wired later through a typed adapter + TaskRunner,
    rather than calling the old modules directly from Kivy.
    """

    def __init__(self, repo_root: str | Path | None = None, logger: Callable[[str], None] | None = None):
        self.repo_root = Path(repo_root or os.getcwd()).resolve()
        self.logger = logger or (lambda _m: None)
        self._networks: list[NetworkObservation] = []

    @property
    def networks(self) -> list[NetworkObservation]:
        return list(self._networks)

    def find_repo_root(self) -> Path:
        candidates = [
            self.repo_root,
            self.repo_root.parent,
            Path.cwd(),
        ]
        for base in candidates:
            if (base / "lazulinet.py").exists() or (base / "debian" / "lazulinet.py").exists():
                self.repo_root = base.resolve()
                return self.repo_root
        return self.repo_root

    def _run(self, argv: list[str], timeout: int = 4) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            argv,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )

    def list_interfaces(self) -> list[WirelessInterface]:
        interfaces: list[WirelessInterface] = []
        seen: set[str] = set()

        if shutil.which("iw"):
            result = self._run(["iw", "dev"])
            current = None
            for raw in result.stdout.splitlines():
                line = raw.strip()
                if line.startswith("Interface "):
                    current = line.split(maxsplit=1)[1].strip()
                    if current and current not in seen:
                        seen.add(current)
                        interfaces.append(WirelessInterface(name=current))
                elif current and line.startswith("type "):
                    mode = line.split(maxsplit=1)[1].strip()
                    for iface in interfaces:
                        if iface.name == current:
                            iface.mode = mode
                            break

        # Fallback/additional interface enumeration.
        sys_class = Path("/sys/class/net")
        if sys_class.exists():
            for child in sorted(sys_class.iterdir()):
                name = child.name
                if name == "lo" or name in seen:
                    continue
                seen.add(name)
                iface = WirelessInterface(name=name)
                try:
                    iface.mac_address = (child / "address").read_text().strip()
                except Exception:
                    pass
                try:
                    iface.is_up = (child / "operstate").read_text().strip() == "up"
                except Exception:
                    pass
                interfaces.append(iface)

        # Enrich existing entries.
        for iface in interfaces:
            base = Path("/sys/class/net") / iface.name
            try:
                iface.mac_address = (base / "address").read_text().strip()
            except Exception:
                pass
            try:
                iface.is_up = (base / "operstate").read_text().strip() == "up"
            except Exception:
                pass
            if (base / "wireless").exists():
                iface.supports_monitor = None

        self.logger(f"Interface refresh: {len(interfaces)} interface(s) detected.")
        return interfaces

    def dependency_status(self) -> dict[str, str]:
        checks = {
            "python": shutil.which("python3") or shutil.which("python") or "",
            "iw": shutil.which("iw") or "",
            "ip": shutil.which("ip") or "",
            "sudo": shutil.which("sudo") or "",
            "airodump-ng": shutil.which("airodump-ng") or "",
        }
        return {name: ("available" if path else "missing") for name, path in checks.items()}

    def privilege_status(self) -> str:
        try:
            if os.geteuid() == 0:
                return "root"
        except AttributeError:
            pass
        if shutil.which("sudo"):
            return "sudo available"
        return "unprivileged"

    def _network_json_candidates(self) -> list[Path]:
        root = self.find_repo_root()
        return [
            root / "networks.json",
            root / "output" / "networks.json",
            root / "debian" / "networks.json",
            root / "debian" / "output" / "networks.json",
            Path.home() / "lazulinet" / "output" / "networks.json",
        ]

    def load_latest_networks(self) -> tuple[list[NetworkObservation], str]:
        existing = [p for p in self._network_json_candidates() if p.exists()]
        if not existing:
            self._networks = []
            self.logger("No networks.json found in known repository/output locations.")
            return [], ""

        source = max(existing, key=lambda p: p.stat().st_mtime)
        raw = json.loads(source.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            if isinstance(raw.get("networks"), list):
                raw = raw["networks"]
            else:
                raw = list(raw.values()) if all(isinstance(v, dict) for v in raw.values()) else []

        self._networks = [
            NetworkObservation.from_mapping(item)
            for item in raw
            if isinstance(item, dict)
        ]
        self.logger(f"Loaded {len(self._networks)} network observation(s) from {source}.")
        return self.networks, str(source)

    def find_sessions(self) -> list[dict[str, str]]:
        root = self.find_repo_root()
        candidates = [
            root / "data" / "sessions",
            root / "sessions",
            root / "debian" / "sessions",
        ]
        sessions: list[dict[str, str]] = []
        for base in candidates:
            if not base.exists():
                continue
            for child in sorted(base.iterdir(), reverse=True):
                if not child.is_dir():
                    continue
                networks = child / "networks.json"
                sessions.append(
                    {
                        "id": child.name,
                        "path": str(child),
                        "networks": "yes" if networks.exists() else "no",
                    }
                )
        self.logger(f"Session refresh: {len(sessions)} session(s) found.")
        return sessions

    def generate_report(self, destination: str | Path | None = None) -> Path:
        root = self.find_repo_root()
        report_dir = Path(destination) if destination else root / "gui_reports"
        report_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now()
        out = report_dir / f"lazulinet_gui_report_{now:%Y%m%d_%H%M%S}.txt"
        lines = [
            "LazuliNet GUI Report",
            f"Generated: {now.isoformat(timespec='seconds')}",
            f"Repository: {root}",
            f"Network observations: {len(self._networks)}",
            "",
        ]
        for idx, n in enumerate(self._networks, 1):
            lines.extend(
                [
                    f"[{idx}] {n.essid or '<hidden>'}",
                    f"  BSSID: {n.bssid}",
                    f"  Channel: {n.channel}",
                    f"  Security: {' / '.join(x for x in [n.privacy, n.cipher, n.auth] if x)}",
                    f"  Signal: {n.signal_power}",
                    f"  Clients: {len(n.clients)}",
                    "",
                ]
            )
        out.write_text("\n".join(lines), encoding="utf-8")
        self.logger(f"Report generated: {out}")
        return out

    def platform_name(self) -> str:
        return f"{platform.system()} {platform.release()}"
