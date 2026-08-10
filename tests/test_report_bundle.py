from __future__ import annotations

import zipfile

from lazulinet.application.report_service import ReportService
from lazulinet.application.session_repository import SessionRepository
from lazulinet.domain.models import NetworkObservation, ScanRequest, SessionStatus


def test_report_bundle_contains_normalized_state_verification_and_raw_artifact(tmp_path):
    repo = SessionRepository(tmp_path / "data")
    session = repo.create("test", ScanRequest(interface="wlan0", duration_seconds=1))
    raw = repo.raw_dir(session.id) / "scan-01.csv"
    raw.write_text("diagnostic")
    repo.add_artifacts(session.id, [raw])
    repo.save_networks(session.id, [NetworkObservation(bssid="AA:BB:CC:DD:EE:FF", essid="lab")])
    repo.set_status(session.id, SessionStatus.COMPLETED, network_count=1)

    bundle = ReportService(repo).export_bundle(session.id)
    with zipfile.ZipFile(bundle) as archive:
        names = set(archive.namelist())
        assert "session/session.json" in names
        assert "session/networks.json" in names
        assert "verification.json" in names
        assert "README.txt" in names
        assert "raw/scan-01.csv" in names
        assert "Verification: PASS" in archive.read("README.txt").decode()
