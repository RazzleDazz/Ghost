import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.monitor import scan_workspace
from core.process_scanner import scan_processes
from core.net_checker import check_loopback
from utils.mcp_stub import handle_mcp_request
from utils.logger import log_event

def main():
    print("=== GHOST SECURITY AGENT: FULL SYSTEM SCAN ===")
    scan_workspace()
    log_event("WORKSPACE_SCAN", {"status": "completed"})
    print("-" * 40)
    scan_processes()
    log_event("PROCESS_SCAN", {"status": "completed"})
    print("-" * 40)
    check_loopback()
    log_event("NET_CHECK", {"status": "completed"})
    print("-" * 40)
    handle_mcp_request()
    log_event("MCP_STUB", {"status": "active"})
    print("=== SCAN COMPLETE ===")

if __name__ == "__main__":
    main()
