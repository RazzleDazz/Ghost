import os
import sys
import time

def scan_workspace():
    print("[*] Scanning workspace for AST and security anomalies...")
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if "eval(" in content or "exec(" in content:
                        print(f"[!] Warning: Potentially unsafe execution pattern found in {filepath}")
if __name__ == "__main__":
    scan_workspace()
