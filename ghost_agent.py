import os, sys, subprocess, importlib.util, sqlite3, shutil, hashlib, time
from datetime import datetime

import psutil

DB_NAME = "ghost_events.db"
POLL_INTERVAL = 10
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
    return free_mb > 10, free_mb

def main():
    print("=== GHOST SECURITY AGENT: CPU SPIKE MONITORING ===")
    init_db()
    try:
        while True:
            disk_ok, free_space = run_health_check()
            procs, spikes = scan_processes()
            self_hash = check_file_integrity("ghost_agent.py")
            
            if spikes:
                spike_msg = f"CPU Spikes detected: {spikes}"
                print(f"[!] {spike_msg}")
                log_event("CPU_SPIKE", spike_msg)
            
            details = f"Disk OK: {disk_ok}, Free: {free_space}MB, Procs: {len(procs)}, Spikes: {len(spikes)}"
            log_event("POLL_CYCLE", details)
            print(f"[{datetime.now().strftime("%H:%M:%S")}] Poll logged -> Procs: {len(procs)} | Spikes: {len(spikes)}")
            
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\n[!] Agent loop stopped by user.")

if __name__ == "__main__":
    main()
