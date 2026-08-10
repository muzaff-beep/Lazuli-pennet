from __future__ import annotations

from threading import Event

from lazulinet.domain.models import ScanRequest
from lazulinet.platform.android.wifi import AndroidWifiAdapter


class ScanResult:
    def __init__(self, bssid, ssid, frequency, level, capabilities="[WPA2-PSK-CCMP][ESS]"):
        self.BSSID = bssid
        self.SSID = ssid
        self.frequency = frequency
        self.level = level
        self.capabilities = capabilities


class FakeWifiManager:
    def __init__(self, initiated=True):
        self.initiated = initiated
        self.results = [
            ScanResult("aa:bb:cc:dd:ee:ff", "Lab 2G", 2437, -42),
            ScanResult("11:22:33:44:55:66", "Lab 5G", 5180, -55),
        ]

    def startScan(self):
        return self.initiated

    def getScanResults(self):
        return self.results

    def isWifiEnabled(self):
        return True


def test_android_scan_normalizes_results_and_filters_channel(tmp_path):
    wifi = FakeWifiManager(initiated=False)  # startScan may be throttled; cached results remain usable.
    adapter = AndroidWifiAdapter(lambda: wifi, wait_cap_seconds=0.01, poll_interval=0.01)
    events = []

    observations, artifacts = adapter.discover(
        ScanRequest(interface="android-wifi", duration_seconds=1, channel=36),
        tmp_path,
        Event(),
        lambda *event: events.append(event),
    )

    assert artifacts == []
    assert len(observations) == 1
    assert observations[0].essid == "Lab 5G"
    assert observations[0].bssid == "11:22:33:44:55:66".upper()
    assert observations[0].channel == 36
    assert observations[0].platform_metadata["android_scan_initiated"] is False
    assert any(event[0] == "ObservationBatch" for event in events)


def test_android_scan_cancellation_returns_without_results(tmp_path):
    wifi = FakeWifiManager()
    adapter = AndroidWifiAdapter(lambda: wifi, wait_cap_seconds=1, poll_interval=0.01)
    cancel = Event()
    cancel.set()

    observations, artifacts = adapter.discover(
        ScanRequest(interface="android-wifi", duration_seconds=10),
        tmp_path,
        cancel,
        lambda *event: None,
    )

    assert observations == []
    assert artifacts == []
