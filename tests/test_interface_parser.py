from lazulinet.domain.models import WirelessMode
from lazulinet.platform.debian.interface import DebianInterfaceAdapter


def test_parse_iw_dev():
    text = """
phy#0
\tInterface wlan0
\t\tifindex 3
\t\twdev 0x1
\t\taddr 12:34:56:78:90:ab
\t\ttype managed
\t\tchannel 6 (2437 MHz), width: 20 MHz
phy#1
\tInterface wlan1mon
\t\taddr aa:bb:cc:dd:ee:ff
\t\ttype monitor
"""
    interfaces = DebianInterfaceAdapter.parse_iw_dev(text)
    assert [i.name for i in interfaces] == ["wlan0", "wlan1mon"]
    assert interfaces[0].mode == WirelessMode.MANAGED
    assert interfaces[1].mode == WirelessMode.MONITOR
