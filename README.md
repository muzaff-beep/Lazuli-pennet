# LazuliNet — WiFi Attack Automation Suite

**"No void unfilled, no target unbroken."**

A comprehensive WiFi penetration testing suite available in two editions:

- **Debian Edition** (`debian/`) — Full modular Python suite for Linux workstations
- **Android Edition** (`android/`) — Single-script Termux deployment for mobile operations

## Features
- Monitor mode management
- Network reconnaissance (2.4/5 GHz)
- WPA/WPA2 handshake capture via deauth
- PMKID capture (clientless attack)
- WPS Pixie Dust attack
- Evil Twin rogue AP
- Hash cracking with hashcat
- Operation reporting

## Quick Start — Debian
```bash
cd debian
sudo python3 lazulinet.py monitor
sudo python3 lazulinet.py scan --timeout 60
sudo python3 lazulinet.py attack --bssid XX:XX:XX:XX:XX:XX --channel 6 --deauth
sudo python3 lazulinet.py crack --capture output/capture_xxx-01.cap
Quick Start — Android (Termux)
bash
cd android
tsu
python lazulinet_mobile.py monitor
python lazulinet_mobile.py scan --time 30
python lazulinet_mobile.py deauth --bssid XX:XX:XX:XX:XX:XX --channel 6
python lazulinet_mobile.py wps --bssid XX:XX:XX:XX:XX:XX --channel 6
python lazulinet_mobile.py crack --file capture-01.cap
Legal
For educational and authorized penetration testing only. Obtain explicit permission before testing any network.
