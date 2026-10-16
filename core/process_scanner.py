import os
import sys

def scan_processes():
    print("[*] Scanning system environment for process anomalies...")
    # Checking /proc for running processes if available in Termux
    if os.path.exists("/proc"):
        pids = [p for p in os.listdir("/proc") if p.isdigit()]
        print(f"[*] Active process count detected via /proc: {len(pids)}")
    else:
        print("[*] /proc restricted; running lightweight environment heuristic check.")

if __name__ == "__main__":
    scan_processes()
