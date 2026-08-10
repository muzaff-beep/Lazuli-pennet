from __future__ import annotations

import json

from lazulinet.cli import main


def test_cli_sessions_on_empty_store(tmp_path, capsys):
    code = main(["--data-dir", str(tmp_path), "sessions"])
    assert code == 0
    assert json.loads(capsys.readouterr().out) == []


def test_cli_report_without_session_is_explicit(tmp_path, capsys):
    code = main(["--data-dir", str(tmp_path), "report"])
    captured = capsys.readouterr()
    assert code == 2
    assert "No normalized session" in captured.err


def test_cli_migrate_legacy_dry_run(tmp_path, capsys):
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "networks.json").write_text('[{"BSSID":"AA:BB:CC:DD:EE:FF","ESSID":"lab"}]')
    data = tmp_path / "data"

    code = main(["--data-dir", str(data), "migrate-legacy", str(legacy), "--dry-run"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload[0]["dry_run"] is True
    assert payload[0]["network_count"] == 1


def test_cli_verify_empty_store(tmp_path, capsys):
    code = main(["--data-dir", str(tmp_path), "verify"])
    assert code == 0
    assert json.loads(capsys.readouterr().out) == []
