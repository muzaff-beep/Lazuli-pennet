from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from lazulinet.domain.errors import ParseError, StorageError
from lazulinet.domain.models import NetworkObservation, ScanRequest, SessionStatus

from .session_repository import SessionRepository


def _canonical_key(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _pick(mapping: dict[str, Any], *names: str, default=None):
    indexed = {_canonical_key(str(key)): value for key, value in mapping.items()}
    for name in names:
        key = _canonical_key(name)
        if key in indexed:
            return indexed[key]
    return default


def _int_or_none(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, float):
            return int(value)
        text = str(value).strip()
        if not text:
            return None
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _clients(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        items = value
    elif isinstance(value, str):
        items = value.replace(";", ",").split(",")
    else:
        items = [value]
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        text = str(item).strip().upper()
        if text and text not in seen:
            seen.add(text)
            output.append(text)
    return output


class LegacyMigrationService:
    """Import historical safe discovery output without executing legacy modules."""

    COMMON_RELATIVE_PATHS = (
        "networks.json",
        "output/networks.json",
        "debian/networks.json",
        "debian/output/networks.json",
    )

    def __init__(self, repo: SessionRepository):
        self.repo = repo
        self._index_path = self.repo.root / "legacy_imports.json"

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _load_index(self) -> dict[str, dict[str, str]]:
        if not self._index_path.exists():
            return {}
        try:
            payload = json.loads(self._index_path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    def _save_index(self, payload: dict[str, dict[str, str]]) -> None:
        self.repo._write_json(self._index_path, payload)

    def find_candidates(self, legacy_root: str | Path) -> list[Path]:
        root = Path(legacy_root).expanduser().resolve()
        candidates: list[Path] = []
        seen: set[Path] = set()

        for relative in self.COMMON_RELATIVE_PATHS:
            path = root / relative
            if path.is_file() and path not in seen:
                seen.add(path)
                candidates.append(path)

        for pattern in ("sessions/*/networks.json", "data/sessions/*/networks.json"):
            for path in sorted(root.glob(pattern), reverse=True):
                resolved = path.resolve()
                if resolved.is_file() and resolved not in seen:
                    seen.add(resolved)
                    candidates.append(resolved)

        return candidates

    @staticmethod
    def _records_from_payload(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if not isinstance(payload, dict):
            raise ParseError("Legacy networks.json must contain an object or list.")

        networks = _pick(payload, "networks")
        if isinstance(networks, list):
            return [item for item in networks if isinstance(item, dict)]

        # A single network object.
        if any(_canonical_key(str(key)) in {"bssid", "essid", "ssid", "channel"} for key in payload):
            return [payload]

        # Mapping keyed by BSSID or another identifier.
        records: list[dict[str, Any]] = []
        for key, value in payload.items():
            if not isinstance(value, dict):
                continue
            record = dict(value)
            if not _pick(record, "bssid") and isinstance(key, str) and ":" in key:
                record["bssid"] = key
            records.append(record)
        return records

    @classmethod
    def normalize_payload(cls, payload: Any) -> list[NetworkObservation]:
        records = cls._records_from_payload(payload)
        normalized: list[NetworkObservation] = []
        by_key: dict[tuple, NetworkObservation] = {}

        for index, record in enumerate(records):
            bssid = str(_pick(record, "bssid", "mac", "ap_mac", default="") or "").strip().upper()
            essid = str(_pick(record, "essid", "ssid", "name", default="") or "").strip()
            channel = _int_or_none(_pick(record, "channel", "ch"))
            privacy = str(_pick(record, "privacy", "security", "encryption", default="") or "").strip()
            cipher = str(_pick(record, "cipher", default="") or "").strip()
            auth = str(_pick(record, "auth", "authentication", "akm", default="") or "").strip()
            signal = _int_or_none(_pick(record, "signal_power", "signal", "power", "rssi", "level"))
            beacons = _int_or_none(_pick(record, "beacons", "beacon_count"))
            data_frames = _int_or_none(_pick(record, "data_frames", "data", "packets"))
            clients = _clients(_pick(record, "clients", "stations", "stations_seen"))
            first_seen = str(_pick(record, "first_seen", "first time seen", "firstseen", default="") or "").strip()
            last_seen = str(_pick(record, "last_seen", "last time seen", "lastseen", default="") or "").strip()

            observation = NetworkObservation(
                bssid=bssid,
                essid=essid,
                channel=channel,
                privacy=privacy,
                cipher=cipher,
                auth=auth,
                signal_power=signal,
                beacons=beacons,
                data_frames=data_frames,
                clients=clients,
                first_seen=first_seen,
                last_seen=last_seen,
                platform_metadata={"legacy_record_index": index},
            )

            # Prefer BSSID as the stable identity. For records without one, retain
            # distinct observations unless their basic visible identity matches.
            key = ("bssid", bssid) if bssid else ("anon", essid, channel, privacy, index if not essid else None)
            current = by_key.get(key)
            if current is None:
                by_key[key] = observation
                normalized.append(observation)
                continue

            # Merge duplicate legacy records conservatively.
            current.clients = list(dict.fromkeys([*current.clients, *observation.clients]))
            for field in ("essid", "privacy", "cipher", "auth", "first_seen", "last_seen"):
                if not getattr(current, field) and getattr(observation, field):
                    setattr(current, field, getattr(observation, field))
            for field in ("channel", "beacons", "data_frames"):
                if getattr(current, field) is None and getattr(observation, field) is not None:
                    setattr(current, field, getattr(observation, field))
            if observation.signal_power is not None:
                if current.signal_power is None or observation.signal_power > current.signal_power:
                    current.signal_power = observation.signal_power

        return normalized

    def inspect_file(self, path: str | Path) -> dict[str, Any]:
        source = Path(path).expanduser().resolve()
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
            networks = self.normalize_payload(payload)
            return {
                "path": str(source),
                "valid": True,
                "network_count": len(networks),
                "error": "",
            }
        except Exception as exc:
            return {
                "path": str(source),
                "valid": False,
                "network_count": 0,
                "error": f"{type(exc).__name__}: {exc}",
            }

    def import_file(self, path: str | Path, *, interface: str = "legacy-import", dry_run: bool = False, force: bool = False) -> dict[str, Any]:
        source = Path(path).expanduser().resolve()
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except Exception as exc:
            raise StorageError(f"Could not read legacy file {source}: {exc}") from exc

        networks = self.normalize_payload(payload)
        source_hash = self._sha256(source)
        index = self._load_index()
        previous = index.get(source_hash)
        previous_session = str(previous.get("session_id", "")) if isinstance(previous, dict) else ""
        duplicate = bool(previous_session and (self.repo.sessions_root / previous_session / "session.json").exists())

        if dry_run:
            return {
                "source": str(source),
                "sha256": source_hash,
                "dry_run": True,
                "duplicate": duplicate,
                "skipped": duplicate and not force,
                "network_count": len(networks),
                "session_id": previous_session if duplicate else "",
            }

        if duplicate and not force:
            return {
                "source": str(source),
                "sha256": source_hash,
                "dry_run": False,
                "duplicate": True,
                "skipped": True,
                "network_count": len(networks),
                "session_id": previous_session,
            }

        session = self.repo.create("legacy-import", ScanRequest(interface=interface, duration_seconds=1))
        raw_target = self.repo.raw_dir(session.id) / "legacy-networks.json"
        try:
            shutil.copy2(source, raw_target)
        except Exception as exc:
            raise StorageError(f"Could not preserve legacy artifact {source}: {exc}") from exc

        self.repo.add_artifacts(session.id, [raw_target])
        self.repo.save_networks(session.id, networks)
        self.repo.set_status(session.id, SessionStatus.COMPLETED, network_count=len(networks))
        index[source_hash] = {"session_id": session.id, "source": str(source)}
        self._save_index(index)
        return {
            "source": str(source),
            "sha256": source_hash,
            "dry_run": False,
            "duplicate": duplicate,
            "skipped": False,
            "network_count": len(networks),
            "session_id": session.id,
        }

    def import_root(self, legacy_root: str | Path, *, interface: str = "legacy-import", dry_run: bool = False, force: bool = False) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for candidate in self.find_candidates(legacy_root):
            try:
                results.append(self.import_file(candidate, interface=interface, dry_run=dry_run, force=force))
            except Exception as exc:
                results.append({
                    "source": str(candidate),
                    "dry_run": dry_run,
                    "network_count": 0,
                    "session_id": "",
                    "error": f"{type(exc).__name__}: {exc}",
                })
        return results
