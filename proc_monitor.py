import os

print("--- Active Process Table Scan ---")
pids = [pid for pid in os.listdir('/proc') if pid.isdigit() and os.path.isdir(os.path.join('/proc', pid))]
print(f"Total active processes detected in /proc: {len(pids)}")
for pid in pids[:10]:
    try:
        with open(os.path.join('/proc', pid, 'comm'), 'r', encoding='utf-8') as f:
            name = f.read().strip()
            print(f"PID {pid}: {name}")
    except Exception:
        pass

print("\n--- Socket Status Check ---")
if os.path.exists('/proc/net/tcp'):
    with open('/proc/net/tcp', 'r', encoding='utf-8') as f:
        lines = f.readlines()[1:]
        print(f"Active TCP socket entries: {len(lines)}")
