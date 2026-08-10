"""Reporter module."""
import os
import json
from datetime import datetime

class Reporter:
    def __init__(self, output_dir):
        self.output_dir = output_dir

    def generate(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.output_dir, f"report_{timestamp}.txt")
        with open(report_file, 'w') as f:
            f.write("="*60 + "\n")
            f.write("LAZULINET - OPERATION REPORT\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write("="*60 + "\n\n")
            json_file = os.path.join(self.output_dir, "networks.json")
            if os.path.exists(json_file):
                with open(json_file) as jf:
                    networks = json.load(jf)
                f.write(f"NETWORKS DISCOVERED: {len(networks)}\n")
                f.write("-"*60 + "\n")
                for net in networks:
                    if not net.get("essid"): continue
                    f.write(f"  ESSID: {net['essid']}\n")
                    f.write(f"  BSSID: {net['bssid']}\n")
                    f.write(f"  Channel: {net['channel']}\n")
                    f.write(f"  Encryption: {net.get('privacy', 'Unknown')}\n\n")
            captures = [x for x in os.listdir(self.output_dir) if x.endswith('.cap') or x.endswith('.22000')]
            if captures:
                f.write("CAPTURE FILES:\n" + "-"*60 + "\n")
                for cap in captures:
                    f.write(f"  {cap} ({os.path.getsize(os.path.join(self.output_dir, cap))} bytes)\n")
        print(f"[*] Report generated: {report_file}")
        with open(report_file, 'r') as f: print(f.read())
