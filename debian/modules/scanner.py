"""Scanner module."""
import os
import subprocess
import time
import json
from datetime import datetime

class Scanner:
    def __init__(self, interface, output_dir):
        self.interface = interface
        self.output_dir = output_dir
        self.networks = []

    def run(self, timeout=60, target_bssid=None, channel=None):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(self.output_dir, f"scan_{timestamp}")
        os.makedirs(self.output_dir, exist_ok=True)

        print(f"\n[*] Scanning for {timeout} seconds...")
        cmd = ["sudo", "airodump-ng", self.interface, "-w", output_file, "--output-format", "csv"]
        if channel: cmd.extend(["-c", str(channel)])
        if target_bssid: cmd.extend(["--bssid", target_bssid])

        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(timeout)
        except KeyboardInterrupt:
            print("\n[!] Scan interrupted")
        finally:
            process.terminate()
            process.wait()
            time.sleep(2)

        self._parse_csv(f"{output_file}-01.csv")
        self._display_results()
        return self.networks

    def _parse_csv(self, csv_file):
        if not os.path.exists(csv_file): return
        with open(csv_file, 'r') as f: content = f.read()
        sections = content.split("\r\n\r\n")
        if len(sections) < 1: return
        network_lines = sections[0].strip().split("\n")
        if len(network_lines) < 2: return
        for line in network_lines[1:]:
            if not line.strip(): continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 14: continue
            net = {
                "bssid": parts[0], "channel": parts[3], "speed": parts[4],
                "privacy": parts[5], "cipher": parts[6], "auth": parts[7],
                "power": parts[8], "beacons": parts[9], "data": parts[10],
                "essid": parts[13] if len(parts) > 13 else "<Hidden>", "clients": []
            }
            self.networks.append(net)

    def _display_results(self):
        print("\n" + "="*90)
        print(f"{'#':<3} {'ESSID':<25} {'BSSID':<18} {'CH':<4} {'ENC':<8} {'PWR':<5} {'CLIENTS':<8}")
        print("="*90)
        for i, net in enumerate(self.networks):
            if not net["essid"]: continue
            print(f"{i:<3} {net['essid']:<25} {net['bssid']:<18} {net['channel']:<4} {net['privacy']:<8} {net['power']:<5} {len(net.get('clients',[])):<8}")
        print("="*90)
        json_file = os.path.join(self.output_dir, "networks.json")
        with open(json_file, 'w') as f: json.dump(self.networks, f, indent=2)
        print(f"[*] Saved to {json_file}")
