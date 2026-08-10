"""Scanner module for LazuliNet."""
import os
import subprocess
import time
import json
import re
from datetime import datetime

class Scanner:
    def __init__(self, interface, output_dir):
        self.interface = interface
        self.output_dir = output_dir
        self.networks = []
        
    def run(self, timeout=60, target_bssid=None, channel=None):
        """Run airodump-ng scan and parse results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(self.output_dir, f"scan_{timestamp}")
        
        print(f"\n[*] Scanning for {timeout} seconds...")
        
        cmd = ["sudo", "airodump-ng", self.interface, "-w", output_file, "--output-format", "csv"]
        if channel:
            cmd.extend(["-c", str(channel)])
        if target_bssid:
            cmd.extend(["--bssid", target_bssid])
        
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        try:
            time.sleep(timeout)
        except KeyboardInterrupt:
            print("\n[!] Scan interrupted by user")
        finally:
            process.terminate()
            process.wait()
            time.sleep(2)
        
        # Parse the CSV output
        self._parse_csv(f"{output_file}-01.csv")
        
        # Display results
        self._display_results()
        
        return self.networks
    
    def _parse_csv(self, csv_file):
        """Parse airodump-ng CSV output."""
        if not os.path.exists(csv_file):
            print(f"[!] CSV file not found: {csv_file}")
            return
        
        with open(csv_file, 'r') as f:
            content = f.read()
        
        # Split networks and clients sections
        sections = content.split("\r\n\r\n")
        
        if len(sections) < 1:
            return
        
        # Parse networks
        network_lines = sections[0].strip().split("\n")
        if len(network_lines) < 2:
            return
        
        headers = [h.strip() for h in network_lines[0].split(",")]
        
        for line in network_lines[1:]:
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 14:
                continue
            
            network = {
                "bssid": parts[0],
                "channel": parts[3],
                "speed": parts[4],
                "privacy": parts[5],
                "cipher": parts[6],
                "auth": parts[7],
                "power": parts[8],
                "beacons": parts[9],
                "data": parts[10],
                "essid": parts[13] if len(parts) > 13 else "<Hidden>"
            }
            self.networks.append(network)
        
        # Parse clients
        if len(sections) > 1:
            client_lines = sections[1].strip().split("\n")
            client_map = {}
            for line in client_lines[1:]:
                if not line.strip():
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 6:
                    continue
                bssid = parts[5]
                client_mac = parts[0]
                if bssid not in client_map:
                    client_map[bssid] = []
                client_map[bssid].append(client_mac)
            
            # Attach clients to networks
            for network in self.networks:
                if network["bssid"] in client_map:
                    network["clients"] = client_map[network["bssid"]]
                else:
                    network["clients"] = []
    
    def _display_results(self):
        """Display scan results in a table."""
        print("\n" + "="*90)
        print(f"{'#':<3} {'ESSID':<25} {'BSSID':<18} {'CH':<4} {'ENC':<8} {'PWR':<5} {'CLIENTS':<8} {'WPS':<5}")
        print("="*90)
        
        for i, net in enumerate(self.networks):
            clients = len(net.get("clients", []))
            power = net.get("power", "?")
            # Skip networks with no ESSID
            if not net["essid"] or net["essid"] == "<Hidden>":
                continue
            print(f"{i:<3} {net['essid']:<25} {net['bssid']:<18} {net['channel']:<4} {net['privacy']:<8} {power:<5} {clients:<8} ?")
        
        print("="*90)
        print(f"[*] Found {len(self.networks)} networks")
        
        # Save to JSON
        json_file = os.path.join(self.output_dir, "networks.json")
        with open(json_file, 'w') as f:
            json.dump(self.networks, f, indent=2)
        print(f"[*] Results saved to {json_file}")
