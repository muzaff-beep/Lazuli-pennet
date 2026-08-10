from __future__ import annotations

import io
import signal
from pathlib import Path
from threading import Event

import pytest

from lazulinet.domain.errors import ParseError, ProcessFailed
from lazulinet.domain.models import ScanRequest
from lazulinet.platform.debian.discovery import DebianDiscoveryAdapter


CSV_TEXT = '''BSSID, First time seen, Last time seen, channel, Speed, Privacy, Cipher, Authentication, Power, # beacons, # IV, LAN IP, ID-length, ESSID, Key\nAA:BB:CC:DD:EE:FF, 2026-08-10 10:00:00, 2026-08-10 10:00:01, 6, 54, WPA2, CCMP, PSK, -42, 3, 1, 0.0.0.0, 3, lab,\n'''


class FakeProcess:
    def __init__(self, returncode=0, polls_before_exit=0, stderr="", on_start=None):
        self.returncode = None if polls_before_exit > 0 else returncode
        self._final_returncode = returncode
        self._polls_before_exit = polls_before_exit
        self.stderr = io.StringIO(stderr)
        self.pid = 999999
        self.terminated = False
        self.killed = False
        if on_start:
            on_start()

    def poll(self):
        if self.returncode is not None:
            return self.returncode
        if self._polls_before_exit <= 0:
            self.returncode = self._final_returncode
            return self.returncode
        self._polls_before_exit -= 1
        return None

    def terminate(self):
        self.terminated = True
        self.returncode = -signal.SIGTERM

    def kill(self):
        self.killed = True
        self.returncode = -signal.SIGKILL

    def wait(self, timeout=None):
        if self.returncode is None:
            self.returncode = self._final_returncode
        return self.returncode


def adapter_for(process):
    return DebianDiscoveryAdapter(
        popen_factory=lambda *args, **kwargs: process,
        command_builder=lambda request, prefix: ["fake-airodump", str(prefix), request.interface],
        poll_interval=0.01,
    )


def test_discovery_process_completes_and_parses(tmp_path):
    raw = tmp_path / "raw"

    def create_csv():
        raw.mkdir(parents=True, exist_ok=True)
        (raw / "scan-01.csv").write_text(CSV_TEXT, encoding="utf-8")

    process = FakeProcess(returncode=0, on_start=create_csv)
    events = []
    networks, artifacts = adapter_for(process).discover(
        ScanRequest(interface="wlan0", duration_seconds=1),
        raw,
        Event(),
        lambda *event: events.append(event),
    )

    assert networks[0].essid == "lab"
    assert artifacts == [raw / "scan-01.csv"]
    assert any(event[0] == "ArtifactCreated" for event in events)


def test_discovery_process_cancellation_preserves_partial_csv(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir(parents=True)
    (raw / "scan-01.csv").write_text(CSV_TEXT, encoding="utf-8")
    process = FakeProcess(returncode=0, polls_before_exit=100)
    cancel = Event()
    cancel.set()

    networks, artifacts = adapter_for(process).discover(
        ScanRequest(interface="wlan0", duration_seconds=5),
        raw,
        cancel,
        lambda *event: None,
    )

    assert process.terminated or process.returncode is not None
    assert len(networks) == 1
    assert artifacts == [raw / "scan-01.csv"]


def test_discovery_process_failure_surfaces_stderr(tmp_path):
    process = FakeProcess(returncode=2, stderr="adapter unavailable")
    with pytest.raises(ProcessFailed, match="adapter unavailable"):
        adapter_for(process).discover(
            ScanRequest(interface="wlan0", duration_seconds=1),
            tmp_path / "raw",
            Event(),
            lambda *event: None,
        )


def test_discovery_process_success_without_artifact_is_parse_error(tmp_path):
    process = FakeProcess(returncode=0)
    with pytest.raises(ParseError, match="without a CSV artifact"):
        adapter_for(process).discover(
            ScanRequest(interface="wlan0", duration_seconds=1),
            tmp_path / "raw",
            Event(),
            lambda *event: None,
        )
