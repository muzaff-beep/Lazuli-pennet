from lazulinet.application.session_repository import SessionRepository
from lazulinet.domain.models import NetworkObservation, ScanRequest, SessionStatus


def test_session_roundtrip(tmp_path):
    repo = SessionRepository(tmp_path)
    session = repo.create("test", ScanRequest(interface="wlan0", duration_seconds=3))
    repo.set_status(session.id, SessionStatus.RUNNING)
    repo.save_networks(session.id, [NetworkObservation(bssid="AA:BB:CC:DD:EE:FF", essid="lab")])
    repo.set_status(session.id, SessionStatus.COMPLETED, network_count=1)

    loaded = repo.load_session(session.id)
    assert loaded.status == SessionStatus.COMPLETED
    assert loaded.network_count == 1
    assert repo.load_networks(session.id)[0].essid == "lab"
    assert repo.latest_completed().id == session.id
