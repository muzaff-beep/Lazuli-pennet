"""Cracker module for LazuliNet."""
import os
import subprocess
import sys

class Cracker:
    def __init__(self, wordlist, output_dir):
        self.wordlist = wordlist
        self.output_dir = output_dir
        
    def crack(self, capture_file, mode=22000):
        """Crack WPA handshake or PMKID with hashcat."""
        
        # If it's a .cap file, convert first
        if capture_file.endswith(".cap"):
            hash_file = capture_file.replace(".cap", ".22000")
            print(f"[*] Converting {capture_file} to hashcat format...")
            
            result = subprocess.run(
                ["hcxpcapngtool", "-o", hash_file, capture_file],
                capture_output=True, text=True
            )
            
            if "EAPOL pairs written" in result.stdout:
                print(f"[✓] Hash file created: {hash_file}")
            else:
                print(f"[!] No valid handshake found in capture")
                print(result.stdout)
                return
        else:
            hash_file = capture_file
        
        if not os.path.exists(hash_file):
            print(f"[!] Hash file not found: {hash_file}")
            return
        
        if not os.path.exists(self.wordlist):
            print(f"[!] Wordlist not found: {self.wordlist}")
            return
        
        print(f"\n[*] Cracking {hash_file}...")
        print(f"[*] Mode: {mode}, Wordlist: {self.wordlist}")
        print("[*] Press Ctrl+C to stop\n")
        
        cmd = [
            "hashcat",
            "-m", str(mode),
            hash_file,
            self.wordlist,
            "--force",
            "--status",
            "--status-timer=10"
        ]
        
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                print(line, end="")
                if "Cracked" in line:
                    print("\n[!] CRACKED! Check output above for password")
        except KeyboardInterrupt:
            print("\n[*] Cracking paused")
            process.terminate()
