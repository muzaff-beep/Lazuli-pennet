"""Utility functions."""
import subprocess
import sys

def banner():
    print("""
╔══════════════════════════════════════════╗
║           LAZULINET v1.0                 ║
║  WiFi Attack Automation Suite            ║
║  "No void unfilled, no target unbroken"  ║
╚══════════════════════════════════════════╝
    """)

def check_root():
    return subprocess.run(["sudo", "-n", "true"], capture_output=True).returncode == 0

def detect_interface():
    result = subprocess.run(["iw", "dev"], capture_output=True, text=True)
    for line in result.stdout.split("\n"):
        if "Interface" in line:
            return line.split()[-1]
    return None

def ensure_monitor_mode(interface):
    result = subprocess.run(["iw", "dev", interface, "info"], capture_output=True, text=True)
    if "type monitor" not in result.stdout:
        print(f"[*] Setting {interface} to monitor mode...")
        subprocess.run(["sudo", "ip", "link", "set", interface, "down"])
        subprocess.run(["sudo", "iw", "dev", interface, "set", "type", "monitor"])
        subprocess.run(["sudo", "ip", "link", "set", interface, "up"])
        print(f"[✓] Monitor mode activated on {interface}")
    else:
        print(f"[✓] {interface} already in monitor mode")

def restore_managed_mode(interface):
    print(f"[*] Restoring {interface} to managed mode...")
    subprocess.run(["sudo", "ip", "link", "set", interface, "down"])
    subprocess.run(["sudo", "iw", "dev", interface, "set", "type", "managed"])
    subprocess.run(["sudo", "ip", "link", "set", interface, "up"])
    print(f"[✓] Managed mode restored on {interface}")
