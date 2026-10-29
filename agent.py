import os
import subprocess

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
    res = subprocess.run(['ip', 'addr'], capture_output=True, text=True)
    print(res.stdout if res.returncode == 0 else 'ip addr failed')

if __name__ == '__main__':
    run_audit()
