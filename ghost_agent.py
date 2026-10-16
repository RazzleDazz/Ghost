import os
import sys
import subprocess
import importlib.util
import sqlite3
import shutil
import hashlib
from datetime import datetime

if importlib.util.find_spec("psutil") is None:
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
    except Exception:
        pass

import psutil

DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ghost_events.db")
ALLOWED_PORTS = [22, 80, 443, 8080]
CPU_THRESHOLD = 50.0

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
    spikes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent"]):
        try:
            pinfo = proc.info
            active_procs.append(pinfo)
            if pinfo["cpu_percent"] and pinfo["cpu_percent"] > CPU_THRESHOLD:
                spikes.append((pinfo["name"], pinfo["pid"], pinfo["cpu_percent"]))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return active_procs, spikes

def check_file_integrity(filepath):
    if not os.path.exists(filepath):
        return None
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def run_health_check():
    home_dir = os.path.expanduser("~")
    _, _, free = shutil.disk_usage(home_dir)
    free_mb = free // (2**20)
    disk_ok = free_mb > 10
    writable = os.access(home_dir, os.W_OK)
    return disk_ok, writable, free_mb

def check_listening_ports():
    anomalies = []
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.status == psutil.CONN_LISTEN:
                port = conn.laddr.port
                if port not in ALLOWED_PORTS:
                    anomalies.append((port, conn.pid))
    except (PermissionError, psutil.AccessDenied):
        pass
    return anomalies

def main():
    init_db()
    disk_ok, writable, free_space = run_health_check()
    procs, spikes = scan_processes()
    script_path = os.path.abspath(__file__)
    self_hash = check_file_integrity(script_path)
    
    if spikes:
        spike_msg = f"CPU Spikes detected: {spikes}"
        log_event("CPU_SPIKE", spike_msg)
        
    anomalies = check_listening_ports()
    if anomalies:
        log_event("PORT_ANOMALY", str(anomalies))
        
    details = f"Disk OK: {disk_ok}, Free: {free_space}MB, Procs: {len(procs)}, Spikes: {len(spikes)}, Hash: {self_hash[:8] if self_hash else 'N/A'}"
    log_event("POLL_CYCLE", details)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Scan complete -> Procs: {len(procs)} | Free Space: {free_space}MB | Spikes: {len(spikes)}")

if __name__ == "__main__":
    main()
