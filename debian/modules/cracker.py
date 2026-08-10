"""Cracker module."""
import os
import subprocess

class Cracker:
    def __init__(self, wordlist, output_dir):
        self.wordlist = wordlist
        self.output_dir = output_dir

    def crack(self, capture_file, mode=22000):
        if capture_file.endswith(".cap"):
            hash_file = capture_file.replace(".cap", ".22000")
            print(f"[*] Converting {capture_file} to hashcat format...")
            subprocess.run(["hcxpcapngtool", "-o", hash_file, capture_file])
            if not os.path.exists(hash_file):
                print("[!] Conversion failed.")
                return
            capture_file = hash_file
        if not os.path.exists(capture_file):
            print(f"[!] File not found: {capture_file}")
            return
        print(f"\n[*] Cracking {capture_file}...")
        cmd = ["hashcat", "-m", str(mode), capture_file, self.wordlist, "--force", "--status", "--status-timer=10"]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                print(line, end="")
                if "Cracked" in line: print("\n[!] CRACKED!")
        except KeyboardInterrupt:
            proc.terminate()
            print("\n[*] Cracking paused.")
