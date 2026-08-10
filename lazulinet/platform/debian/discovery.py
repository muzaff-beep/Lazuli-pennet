from __future__ import annotations

import csv
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from threading import Event

from lazulinet.domain.errors import DependencyMissing, ParseError, PrivilegeUnavailable, ProcessFailed
from lazulinet.domain.models import NetworkObservation, ScanRequest
from lazulinet.domain.validation import validate_channel, validate_duration, validate_interface_name
from lazulinet.ports.interfaces import EventEmitter


def _int_or_none(value: str | None) -> int | None:
    try:
        return int((value or "").strip())
    except (TypeError, ValueError):
        return None


def _norm(value: str) -> str:
    return " ".join(value.strip().lower().split())


class AirodumpCsvParser:
    """Parses airodump-ng CSV using Python's CSV parser, including quoted ESSIDs."""

    def parse(self, path: str | Path) -> list[NetworkObservation]:
        path = Path(path)
        if not path.exists():
            raise ParseError(f"Discovery CSV was not created: {path}")

        aps: dict[str, NetworkObservation] = {}
        section = ""
        header: list[str] = []
        try:
            with path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
                for raw_row in csv.reader(fh, skipinitialspace=True):
                    row = [cell.strip() for cell in raw_row]
                    if not row or not any(row):
                        continue
                    first = _norm(row[0])
                    if first == "bssid":
                        section = "ap"
                        header = [_norm(cell) for cell in row]
                        continue
                    if first == "station mac":
                        section = "station"
                        header = [_norm(cell) for cell in row]
                        continue
                    if not header or section not in ("ap", "station"):
                        continue
                    if len(row) < len(header):
                        row += [""] * (len(header) - len(row))
                    record = dict(zip(header, row))
                    if section == "ap":
                        bssid = record.get("bssid", "").upper().strip()
                        if not bssid:
                            continue
                        aps[bssid] = NetworkObservation(
                            bssid=bssid,
                            essid=record.get("essid", "").strip(),
                            channel=_int_or_none(record.get("channel")),
                            privacy=record.get("privacy", "").strip(),
                            cipher=record.get("cipher", "").strip(),
                            auth=record.get("authentication", "").strip(),
                            signal_power=_int_or_none(record.get("power")),
                            beacons=_int_or_none(record.get("# beacons")),
                            data_frames=_int_or_none(record.get("# iv")),
                            first_seen=record.get("first time seen", "").strip(),
                            last_seen=record.get("last time seen", "").strip(),
                        )
                    else:
                        station = record.get("station mac", "").upper().strip()
                        bssid = record.get("bssid", "").upper().strip()
                        if station and bssid in aps and station not in aps[bssid].clients:
                            aps[bssid].clients.append(station)
        except csv.Error as exc:
            raise ParseError(f"Invalid discovery CSV: {exc}") from exc
        return list(aps.values())


class DebianDiscoveryAdapter:
    platform_name = "debian"

    def __init__(
        self,
        parser: AirodumpCsvParser | None = None,
        popen_factory=None,
        command_builder=None,
        poll_interval: float = 0.2,
    ):
        self.parser = parser or AirodumpCsvParser()
        self._popen = popen_factory or subprocess.Popen
        self._command_builder = command_builder or self._command
        self._poll_interval = max(0.01, float(poll_interval))

    @staticmethod
    def _command(request: ScanRequest, prefix: Path) -> list[str]:
        binary = shutil.which("airodump-ng")
        if not binary:
            raise DependencyMissing("Required dependency is missing: airodump-ng")
        args = [binary, "--write", str(prefix), "--output-format", "csv"]
        if request.channel is not None:
            args.extend(["--channel", str(request.channel)])
        args.append(request.interface)
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            return args
        sudo = shutil.which("sudo")
        if not sudo:
            raise PrivilegeUnavailable("Discovery requires root privilege or non-interactive sudo.")
        return [sudo, "-n", *args]

    @staticmethod
    def _stop_process(process: subprocess.Popen) -> None:
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except Exception:
            process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except Exception:
                process.kill()
            process.wait(timeout=2)

    def discover(self, request: ScanRequest, raw_dir: Path, cancel_event: Event, emit: EventEmitter):
        request.interface = validate_interface_name(request.interface)
        request.duration_seconds = validate_duration(request.duration_seconds)
        request.channel = validate_channel(request.channel)
        raw_dir.mkdir(parents=True, exist_ok=True)
        prefix = raw_dir / "scan"
        command = self._command_builder(request, prefix)
        emit("LogLine", f"Starting passive discovery on {request.interface}", 0.05, None)

        process = self._popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        started = time.monotonic()
        try:
            while process.poll() is None:
                elapsed = time.monotonic() - started
                if cancel_event.is_set() or elapsed >= request.duration_seconds:
                    break
                emit("ProgressChanged", "Discovery running", min(0.9, 0.05 + 0.8 * elapsed / request.duration_seconds), None)
                cancel_event.wait(self._poll_interval)
        finally:
            self._stop_process(process)

        if cancel_event.is_set():
            emit("LogLine", "Discovery cancelled; preserving any raw artifact produced so far.", 0.9, None)
        elif process.returncode not in (0, -signal.SIGTERM, -signal.SIGKILL):
            stderr = ""
            try:
                stderr = (process.stderr.read() if process.stderr else "").strip()
            except Exception:
                pass
            if not list(raw_dir.glob("scan-*.csv")):
                raise ProcessFailed(stderr or f"airodump-ng exited with {process.returncode}")

        csv_files = sorted(raw_dir.glob("scan-*.csv"))
        if not csv_files:
            if cancel_event.is_set():
                return [], []
            raise ParseError("Discovery finished without a CSV artifact.")
        csv_path = csv_files[-1]
        emit("ArtifactCreated", str(csv_path), 0.92, {"path": str(csv_path)})
        networks = self.parser.parse(csv_path)
        return networks, csv_files
