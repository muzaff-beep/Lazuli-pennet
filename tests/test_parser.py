from pathlib import Path

from lazulinet.platform.debian.discovery import AirodumpCsvParser


def test_airodump_csv_parser_handles_quoted_essid_and_clients():
    path = Path(__file__).parent / "fixtures" / "airodump_sample.csv"
    networks = AirodumpCsvParser().parse(path)
    assert len(networks) == 2
    first = next(n for n in networks if n.bssid == "AA:BB:CC:DD:EE:FF")
    assert first.essid == "Lab, Network"
    assert first.channel == 6
    assert first.signal_power == -42
    assert first.clients == ["77:88:99:AA:BB:CC"]
