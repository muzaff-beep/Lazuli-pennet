from __future__ import annotations

import time

from lazulinet.application.services import DiscoveryService
from lazulinet.application.session_repository import SessionRepository
from lazulinet.application.task_runner import TaskRunner
from lazulinet.domain.models import NetworkObservation, ScanRequest, SessionStatus, TaskState


def wait_terminal(handle, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snap = handle.snapshot()
        if snap.state in (TaskState.COMPLETED, TaskState.CANCELLED, TaskState.FAILED):
            return snap
        time.sleep(0.01)
    raise AssertionError("task did not finish")


class CancelAwareAdapter:
    platform_name = "fake"

    def discover(self, request, raw_dir, cancel_event, emit):
        cancel_event.wait(0.05)
        return [NetworkObservation(bssid="AA:BB:CC:DD:EE:FF", essid="partial")], []


class FailingAdapter:
    platform_name = "fake"

    def discover(self, request, raw_dir, cancel_event, emit):
        artifact = raw_dir / "diagnostic.csv"
        artifact.write_text("partial", encoding="utf-8")
        raise RuntimeError("fixture failure")


def test_cancelled_scan_persists_partial_normalized_results(tmp_path):
    repo = SessionRepository(tmp_path)
    service = DiscoveryService(CancelAwareAdapter(), repo, TaskRunner())
    handle = service.start_scan(ScanRequest(interface="wlan0", duration_seconds=2))
    time.sleep(0.01)
    handle.cancel()
    snap = wait_terminal(handle)

    assert snap.state == TaskState.CANCELLED
    session = repo.load_session(snap.result["session_id"])
    assert session.status == SessionStatus.CANCELLED
    assert repo.load_networks(session.id)[0].essid == "partial"
    assert repo.latest_with_networks().id == session.id


def test_failed_scan_records_raw_diagnostic_artifact(tmp_path):
    repo = SessionRepository(tmp_path)
    service = DiscoveryService(FailingAdapter(), repo, TaskRunner())
    handle = service.start_scan(ScanRequest(interface="wlan0", duration_seconds=1))
    snap = wait_terminal(handle)

    assert snap.state == TaskState.FAILED
    session_id = service.session_for_task(handle.id)
    session = repo.load_session(session_id)
    assert session.status == SessionStatus.FAILED
    assert session.error.startswith("RuntimeError: fixture failure")
    assert "raw/diagnostic.csv" in session.raw_artifacts
