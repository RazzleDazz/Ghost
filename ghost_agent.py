import os, sys, subprocess, importlib.util, sqlite3, shutil
from datetime import datetime

import psutil

DB_NAME = "ghost_events.db"
ALLOWED_PORTS = [22, 80, 443, 8080]

def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, event_type TEXT, details TEXT)")
    conn.commit()
    conn.close()

def log_event(event_type, details):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT INTO events (timestamp, event_type, details) VALUES (?, ?, ?)", (datetime.now().isoformat(), event_type, details))
    conn.commit()
    conn.close()

def scan_processes():
    active_procs = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent"]):
        try:
            active_procs.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return active_procs

def check_listening_ports():
    anomalies = []
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.status == psutil.CONN_LISTEN:
                port = conn.laddr.port
                if port not in ALLOWED_PORTS:
                    anomalies.append((port, conn.pid))
    except (PermissionError, psutil.AccessDenied):
        print("[!] Note: Network socket inspection restricted by Android permissions.")
    return anomalies

def run_health_check():
    _, _, free = shutil.disk_usage("/")
    free_mb = free // (2**20)
    disk_ok = free_mb > 100
    writable = os.access(".", os.W_OK)
    return disk_ok, writable, free_mb

def main():
    print("=== GHOST SECURITY AGENT: UNIFIED DIAGNOSTIC ===")
    init_db()
    disk_ok, writable, free_space = run_health_check()
    print(f"[*] Health Check -> Disk Writable: {writable} | Free Space: {free_space} MB")
    log_event("HEALTH_CHECK", f"Disk OK: {disk_ok}, Free Space: {free_space}MB")
    procs = scan_processes()
    print(f"[*] Process Scan -> Total Active Processes: {len(procs)}")
    anomalies = check_listening_ports()
    if anomalies:
        print(f"[!] WARNING: Unexpected listening ports detected: {anomalies}")
        log_event("PORT_ANOMALY", str(anomalies))
    else:
        print("[+] Port Check -> Completed safely.")
    print("=== SCAN COMPLETE. EVENTS LOGGED TO DATABASE. ===")

if __name__ == "__main__":
    main()
