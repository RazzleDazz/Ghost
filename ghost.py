import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.monitor import scan_workspace
from core.process_scanner import scan_processes
from utils.mcp_stub import handle_mcp_request

def main():
    print("=== GHOST SECURITY AGENT: FULL SYSTEM SCAN ===")
    scan_workspace()
    print("-" * 40)
    scan_processes()
    print("-" * 40)
    handle_mcp_request()
    print("=== SCAN COMPLETE ===")

if __name__ == "__main__":
    main()
