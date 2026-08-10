"""Reporter module for LazuliNet."""
import os
import json
from datetime import datetime

class Reporter:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        
    def generate(self):
        """Generate a summary report of all findings."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.output_dir, f"report_{timestamp}.txt")
        
        with open(report_file, 'w') as f:
            f.write("="*60 + "\n")
            f.write("LAZULINET - OPERATION REPORT\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write("="*60 + "\n\n")
            
            # Load networks
            json_file = os.path.join(self.output_dir, "networks.json")
            if os.path.exists(json_file):
                with open(json_file) as jf:
                    networks = json.load(jf)
                
                f.write(f"NETWORKS DISCOVERED: {len(networks)}\n")
                f.write("-"*60 + "\n")
                
                for net in networks:
                    if not net.get("essid"):
                        continue
                    f.write(f"  ESSID: {net['essid']}\n")
                    f.write(f"  BSSID: {net['bssid']}\n")
                    f.write(f"  Channel: {net['channel']}\n")
                    f.write(f"  Encryption: {net.get('privacy', 'Unknown')}\n")
                    f.write(f"  Clients: {len(net.get('clients', []))}\n")
                    if net.get('clients'):
                        f.write(f"  Client MACs: {', '.join(net['clients'])}\n")
                    f.write("\n")
            
            # List captures
            captures = [f for f in os.listdir(self.output_dir) if f.endswith('.cap') or f.endswith('.22000')]
            if captures:
                f.write("CAPTURE FILES:\n")
                f.write("-"*60 + "\n")
                for cap in captures:
                    size = os.path.getsize(os.path.join(self.output_dir, cap))
                    f.write(f"  {cap} ({size} bytes)\n")
        
        print(f"[*] Report generated: {report_file}")
        
        # Print to terminal
        with open(report_file, 'r') as f:
            print(f.read())
