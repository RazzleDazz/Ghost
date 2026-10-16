#!/bin/bash
python3 /data/data/com.termux/files/home/ghost_agent/agent.py "Audit active network interfaces, check open local sockets, enumerate installed security binaries in Termux path, and save findings to security_audit.log."
cp /data/data/com.termux/files/home/ghost_agent/workspace/security_audit.log /data/data/com.termux/files/home/storage/shared/Download/
