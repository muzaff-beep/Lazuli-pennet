from lazulinet.application.services import DiscoveryService
from lazulinet.application.session_repository import SessionRepository
from lazulinet.application.task_runner import TaskRunner
from lazulinet.domain.models import NetworkObservation, ScanRequest, TaskState
import time


class FakeAdapter:
    platform_name = "fake"

    def discover(self, request, raw_dir, cancel_event, emit):
        emit("ProgressChanged", "fake", 0.5, None)
        return [NetworkObservation(bssid="AA:BB:CC:DD:EE:FF", essid="fixture")], []


def test_discovery_service_creates_completed_session(tmp_path):
    repo = SessionRepository(tmp_path)
    runner = TaskRunner()
    service = DiscoveryService(FakeAdapter(), repo, runner)
    handle = service.start_scan(ScanRequest(interface="wlan0", duration_seconds=1))
    deadline = time.monotonic() + 2
    while handle.snapshot().state not in (TaskState.COMPLETED, TaskState.FAILED):
        assert time.monotonic() < deadline
        time.sleep(0.01)
    assert handle.snapshot().state == TaskState.COMPLETED
    session_id = handle.snapshot().result["session_id"]
    assert repo.load_networks(session_id)[0].essid == "fixture"
