from __future__ import annotations

import json

from lazulinet.application.legacy_migration import LegacyMigrationService
from lazulinet.application.session_repository import SessionRepository


def test_normalize_common_legacy_fields_and_deduplicate_clients(tmp_path):
    service = LegacyMigrationService(SessionRepository(tmp_path / "data"))
    payload = [
        {
            "BSSID": "aa:bb:cc:dd:ee:ff",
            "ESSID": "Cafe, Lab",
            "Channel": "6",
            "Privacy": "WPA2",
            "Cipher": "CCMP",
            "Authentication": "PSK",
            "Power": "-61",
            "clients": ["11:22:33:44:55:66"],
        },
        {
            "bssid": "AA:BB:CC:DD:EE:FF",
            "ssid": "Cafe, Lab",
            "channel": 6,
            "rssi": -48,
            "stations": "11:22:33:44:55:66, 22:33:44:55:66:77",
        },
    ]

    networks = service.normalize_payload(payload)
    assert len(networks) == 1
    assert networks[0].bssid == "AA:BB:CC:DD:EE:FF"
    assert networks[0].essid == "Cafe, Lab"
    assert networks[0].channel == 6
    assert networks[0].signal_power == -48
    assert networks[0].clients == ["11:22:33:44:55:66", "22:33:44:55:66:77"]


def test_mapping_key_can_supply_bssid(tmp_path):
    service = LegacyMigrationService(SessionRepository(tmp_path / "data"))
    payload = {
        "AA:BB:CC:DD:EE:01": {"ESSID": "one", "Channel": 1},
        "AA:BB:CC:DD:EE:02": {"ESSID": "two", "Channel": 11},
    }
    networks = service.normalize_payload(payload)
    assert [n.bssid for n in networks] == ["AA:BB:CC:DD:EE:01", "AA:BB:CC:DD:EE:02"]


def test_import_preserves_source_artifact_and_verifies(tmp_path):
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    source = legacy / "networks.json"
    source.write_text(json.dumps({"networks": [{"BSSID": "AA:BB:CC:DD:EE:FF", "ESSID": "lab"}]}))

    repo = SessionRepository(tmp_path / "new")
    service = LegacyMigrationService(repo)
    result = service.import_file(source)

    assert result["network_count"] == 1
    session = repo.load_session(result["session_id"])
    assert session.platform == "legacy-import"
    assert session.network_count == 1
    assert repo.load_networks(session.id)[0].essid == "lab"
    verification = repo.verify(session.id)
    assert verification["ok"] is True
    assert verification["artifacts_ok"] is True
    assert (repo.raw_dir(session.id) / "legacy-networks.json").exists()


def test_dry_run_does_not_create_session(tmp_path):
    source = tmp_path / "networks.json"
    source.write_text(json.dumps([{"BSSID": "AA:BB:CC:DD:EE:FF"}]))
    repo = SessionRepository(tmp_path / "data")
    service = LegacyMigrationService(repo)

    result = service.import_file(source, dry_run=True)
    assert result["dry_run"] is True
    assert result["network_count"] == 1
    assert repo.list_sessions() == []


def test_find_candidates_uses_known_safe_output_locations(tmp_path):
    for relative in ("networks.json", "output/networks.json", "debian/output/networks.json"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[]")

    service = LegacyMigrationService(SessionRepository(tmp_path / "data"))
    found = service.find_candidates(tmp_path)
    assert {path.relative_to(tmp_path).as_posix() for path in found} == {
        "networks.json",
        "output/networks.json",
        "debian/output/networks.json",
    }


def test_import_is_idempotent_by_source_hash(tmp_path):
    source = tmp_path / "networks.json"
    source.write_text(json.dumps([{"BSSID": "AA:BB:CC:DD:EE:FF", "ESSID": "lab"}]))
    repo = SessionRepository(tmp_path / "data")
    service = LegacyMigrationService(repo)

    first = service.import_file(source)
    second = service.import_file(source)

    assert first["skipped"] is False
    assert second["skipped"] is True
    assert second["duplicate"] is True
    assert second["session_id"] == first["session_id"]
    assert len(repo.list_sessions()) == 1


def test_force_import_allows_duplicate_source_as_new_session(tmp_path):
    source = tmp_path / "networks.json"
    source.write_text(json.dumps([{"BSSID": "AA:BB:CC:DD:EE:FF"}]))
    repo = SessionRepository(tmp_path / "data")
    service = LegacyMigrationService(repo)

    first = service.import_file(source)
    second = service.import_file(source, force=True)

    assert second["skipped"] is False
    assert second["duplicate"] is True
    assert second["session_id"] != first["session_id"]
    assert len(repo.list_sessions()) == 2
