from __future__ import annotations

import json
import zipfile
from pathlib import Path

from .session_repository import SessionRepository


class ReportService:
    def __init__(self, repo: SessionRepository):
        self.repo = repo

    def generate_text(self, session_id: str) -> Path:
        session = self.repo.load_session(session_id)
        networks = self.repo.load_networks(session_id)
        out = self.repo.root / "reports" / f"report_{session_id}.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "LazuliNet Discovery Report",
            f"Session: {session.id}",
            f"Platform: {session.platform}",
            f"Interface: {session.interface}",
            f"Started: {session.started_at}",
            f"Ended: {session.ended_at}",
            f"Status: {session.status.value}",
            f"Networks: {len(networks)}",
            "",
        ]
        for idx, n in enumerate(networks, 1):
            lines.extend([
                f"[{idx}] {n.essid or '<hidden>'}",
                f"  BSSID: {n.bssid}",
                f"  Channel: {n.channel if n.channel is not None else '—'}",
                f"  Security: {' / '.join(x for x in (n.privacy, n.cipher, n.auth) if x) or '—'}",
                f"  Signal: {n.signal_power if n.signal_power is not None else '—'}",
                f"  Clients: {len(n.clients)}",
                "",
            ])
        out.write_text("\n".join(lines), encoding="utf-8")
        return out

    def export_json(self, session_id: str) -> Path:
        session = self.repo.load_session(session_id)
        networks = self.repo.load_networks(session_id)
        out = self.repo.root / "reports" / f"report_{session_id}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            "session": session.to_dict(),
            "networks": [n.to_dict() for n in networks],
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        return out

    def export_bundle(self, session_id: str) -> Path:
        """Create a portable evidence bundle from one normalized session."""
        session = self.repo.load_session(session_id)
        session_dir = self.repo.sessions_root / session_id
        out = self.repo.root / "reports" / f"bundle_{session_id}.zip"
        out.parent.mkdir(parents=True, exist_ok=True)
        verification = self.repo.verify(session_id)

        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
            for name in ("session.json", "networks.json"):
                path = session_dir / name
                if path.exists():
                    archive.write(path, f"session/{name}")

            archive.writestr(
                "verification.json",
                json.dumps(verification, indent=2, ensure_ascii=False),
            )

            for value in session.raw_artifacts:
                artifact = Path(value)
                if not artifact.is_absolute():
                    artifact = session_dir / artifact
                if artifact.exists() and artifact.is_file():
                    archive.write(artifact, f"raw/{artifact.name}")

            networks = self.repo.load_networks(session_id)
            summary = [
                "LazuliNet Session Bundle",
                f"Session: {session.id}",
                f"Status: {session.status.value}",
                f"Platform: {session.platform}",
                f"Interface: {session.interface}",
                f"Networks: {len(networks)}",
                f"Verification: {'PASS' if verification['ok'] else 'FAIL'}",
            ]
            archive.writestr("README.txt", "\n".join(summary) + "\n")
        return out

