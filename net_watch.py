import time, os

print("--- Starting Continuous Process & Port Watcher ---")
try:
    while True:
        pids = [p for p in os.listdir('/proc') if p.isdigit()]
        tcp_count = 0
        if os.path.exists('/proc/net/tcp'):
            with open('/proc/net/tcp', 'r') as f:
                tcp_count = len(f.readlines()) - 1
        print(f"[STATUS] Active PIDs: {len(pids)} | Active TCP Sockets: {tcp_count}")
        time.sleep(5)
except KeyboardInterrupt:
    print("\nWatcher stopped.")
