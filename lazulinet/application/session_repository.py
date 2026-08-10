from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from lazulinet.domain.errors import StorageError
from lazulinet.domain.models import NetworkObservation, ScanRequest, ScanSession, SessionStatus


def default_data_root() -> Path:
    override = os.environ.get("LAZULINET_DATA_DIR")
    if override:
        return Path(override).expanduser()
    if os.environ.get("ANDROID_ARGUMENT"):
        private = os.environ.get("ANDROID_PRIVATE") or os.environ.get("HOME") or "."
        return Path(private) / "lazulinet-data"
    return Path.home() / ".local" / "share" / "lazulinet"


class SessionRepository:
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root) if root else default_data_root()
        self.sessions_root = self.root / "sessions"
        self.sessions_root.mkdir(parents=True, exist_ok=True)

    def _session_dir(self, session_id: str) -> Path:
        return self.sessions_root / session_id

    def create(self, platform: str, request: ScanRequest) -> ScanSession:
        now = datetime.now(timezone.utc)
        session_id = f"{now:%Y%m%dT%H%M%SZ}_{uuid.uuid4().hex[:8]}"
        path = self._session_dir(session_id)
        (path / "raw").mkdir(parents=True, exist_ok=False)
        (path / "logs").mkdir(parents=True, exist_ok=True)
        session = ScanSession(
            id=session_id,
            platform=platform,
            interface=request.interface,
            started_at=now.isoformat(timespec="seconds"),
            channel_filter=request.channel,
        )
        self.save_session(session)
        return session

    def raw_dir(self, session_id: str) -> Path:
        path = self._session_dir(session_id) / "raw"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_session(self, session: ScanSession) -> None:
        self._write_json(self._session_dir(session.id) / "session.json", session.to_dict())

    def set_status(self, session_id: str, status: SessionStatus, *, error: str = "", network_count: int | None = None) -> ScanSession:
        session = self.load_session(session_id)
        session.status = status
        if status in (SessionStatus.COMPLETED, SessionStatus.CANCELLED, SessionStatus.FAILED):
            session.ended_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        session.error = error
        if network_count is not None:
            session.network_count = network_count
        self.save_session(session)
        return session

    def add_artifacts(self, session_id: str, paths: list[Path]) -> None:
        session = self.load_session(session_id)
        base = self._session_dir(session_id)
        for path in paths:
            try:
                value = str(path.resolve().relative_to(base.resolve()))
            except Exception:
                value = str(path)
            if value not in session.raw_artifacts:
                session.raw_artifacts.append(value)
        self.save_session(session)

    def save_networks(self, session_id: str, networks: list[NetworkObservation]) -> None:
        self._write_json(
            self._session_dir(session_id) / "networks.json",
            [network.to_dict() for network in networks],
        )
        session = self.load_session(session_id)
        session.network_count = len(networks)
        self.save_session(session)

    def load_networks(self, session_id: str) -> list[NetworkObservation]:
        path = self._session_dir(session_id) / "networks.json"
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return [NetworkObservation.from_dict(item) for item in raw if isinstance(item, dict)]
        except Exception as exc:
            raise StorageError(f"Could not read {path}: {exc}") from exc

    def load_session(self, session_id: str) -> ScanSession:
        path = self._session_dir(session_id) / "session.json"
        try:
            return ScanSession.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception as exc:
            raise StorageError(f"Could not read session {session_id}: {exc}") from exc

    def list_sessions(self, limit: int = 100) -> list[ScanSession]:
        sessions: list[ScanSession] = []
        for path in sorted(self.sessions_root.glob("*/session.json"), reverse=True):
            try:
                sessions.append(ScanSession.from_dict(json.loads(path.read_text(encoding="utf-8"))))
            except Exception:
                continue
            if len(sessions) >= limit:
                break
        return sessions

    def latest_completed(self) -> ScanSession | None:
        for session in self.list_sessions():
            if session.status == SessionStatus.COMPLETED:
                return session
        return None

    @staticmethod
    def _write_json(path: Path, payload) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
        except Exception as exc:
            raise StorageError(f"Could not write {path}: {exc}") from exc
