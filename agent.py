import os
import subprocess
import socket

def run_audit():
    print("=== NUMUNA GHOST CYBERWORKS - SYSTEM SECURITY AUDIT ===")
    path_dirs = os.environ.get('PATH', '').split(':')
    binaries = ['nmap', 'tcpdump', 'tshark', 'nc', 'netcat', 'socat', 'openssl', 'gpg', 'ncat', 'python3']
    found = {}
    for b in binaries:
        for d in path_dirs:
            full_path = os.path.join(d, b)
            if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                found[b] = full_path
                break
    print('Found security/network binaries:', found)
    
    print('\n--- Active Listening Sockets ---')
    try:
        res = subprocess.run(['ss', '-tuln'], capture_output=True, text=True)
        print(res.stdout if res.returncode == 0 else subprocess.run(['netstat', '-tuln'], capture_output=True, text=True).stdout)
    except Exception as e:
        print('Socket check error:', e)
        
    print('\n--- Active Network Interfaces ---')
    try:
        res = subprocess.run(['ifconfig'], capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            print(res.stdout)
        else:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            print(f"Hostname: {hostname}\nLocal IP (Socket): {local_ip}")
    except Exception as e:
        print('Interface check error:', e)

if __name__ == '__main__':
    run_audit()
