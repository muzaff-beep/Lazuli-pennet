from __future__ import annotations

from dataclasses import dataclass

from lazulinet.domain.models import ScanRequest, SessionStatus, WirelessMode
from lazulinet.domain.validation import validate_channel, validate_duration, validate_interface_name
from lazulinet.ports.interfaces import DiscoveryAdapter, InterfaceAdapter

from .session_repository import SessionRepository
from .task_runner import TaskHandle, TaskRunner


class InterfaceService:
    def __init__(self, adapter: InterfaceAdapter):
        self.adapter = adapter

    def list_interfaces(self):
        return self.adapter.list_interfaces()

    def set_mode(self, interface: str, mode: WirelessMode):
        return self.adapter.set_mode(validate_interface_name(interface), mode)

    def health(self) -> dict[str, str]:
        return {
            "platform": self.adapter.platform_name,
            "privilege": self.adapter.privilege_status(),
            **self.adapter.dependency_status(),
        }


class DiscoveryService:
    def __init__(self, adapter: DiscoveryAdapter, repo: SessionRepository, runner: TaskRunner):
        self.adapter = adapter
        self.repo = repo
        self.runner = runner
        self._task_sessions: dict[str, str] = {}

    def start_scan(self, request: ScanRequest) -> TaskHandle:
        request.interface = validate_interface_name(request.interface)
        request.duration_seconds = validate_duration(request.duration_seconds)
        request.channel = validate_channel(request.channel)
        session = self.repo.create(self.adapter.platform_name, request)
        self.repo.set_status(session.id, SessionStatus.RUNNING)

        def worker(cancel_event, emit):
            raw_dir = self.repo.raw_dir(session.id)
            emit("SessionCreated", f"Session {session.id}", 0.02, {"session_id": session.id})
            try:
                networks, artifacts = self.adapter.discover(request, raw_dir, cancel_event, emit)
                self.repo.add_artifacts(session.id, artifacts)

                # Persist normalized partial results too. A cancelled discovery session is
                # still useful for history/reporting and should not silently discard data.
                self.repo.save_networks(session.id, networks)

                if cancel_event.is_set():
                    self.repo.set_status(session.id, SessionStatus.CANCELLED, network_count=len(networks))
                    return {"session_id": session.id, "network_count": len(networks), "cancelled": True}

                self.repo.set_status(session.id, SessionStatus.COMPLETED, network_count=len(networks))
                emit("ObservationBatch", f"{len(networks)} network(s) normalized", 0.95, {"count": len(networks)})
                return {"session_id": session.id, "network_count": len(networks), "cancelled": False}
            except Exception as exc:
                # Preserve any raw files that exist even when parsing/process execution
                # fails so diagnosis is possible from the failed session.
                raw_files = [path for path in raw_dir.rglob("*") if path.is_file()]
                if raw_files:
                    self.repo.add_artifacts(session.id, raw_files)
                self.repo.set_status(session.id, SessionStatus.FAILED, error=f"{type(exc).__name__}: {exc}")
                raise

        handle = self.runner.submit("discovery", worker)
        self._task_sessions[handle.id] = session.id
        return handle

    def session_for_task(self, task_id: str) -> str | None:
        return self._task_sessions.get(task_id)


@dataclass(slots=True)
class LazuliRuntime:
    interface: InterfaceService
    discovery: DiscoveryService
    sessions: SessionRepository
    tasks: TaskRunner
