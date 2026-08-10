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
