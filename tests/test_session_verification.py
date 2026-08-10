from __future__ import annotations

from lazulinet.application.session_repository import SessionRepository
from lazulinet.domain.models import NetworkObservation, ScanRequest, SessionStatus


def test_verify_detects_network_count_mismatch(tmp_path):
    repo = SessionRepository(tmp_path)
    session = repo.create("test", ScanRequest(interface="wlan0", duration_seconds=1))
    repo.save_networks(session.id, [NetworkObservation(bssid="AA:BB:CC:DD:EE:FF")])
    repo.set_status(session.id, SessionStatus.COMPLETED, network_count=2)

    result = repo.verify(session.id)
    assert result["ok"] is False
    assert result["stored_network_count"] == 2
    assert result["actual_network_count"] == 1
    assert result["network_count_matches"] is False


def test_verify_detects_missing_recorded_artifact(tmp_path):
    repo = SessionRepository(tmp_path)
    session = repo.create("test", ScanRequest(interface="wlan0", duration_seconds=1))
    session.raw_artifacts.append("raw/does-not-exist.csv")
    repo.save_session(session)

    result = repo.verify(session.id)
    assert result["ok"] is False
    assert result["artifacts_ok"] is False
