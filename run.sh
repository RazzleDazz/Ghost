#!/bin/bash
cd ~/ghost_agent
python3 agent.py > workspace/security_audit.log
git add workspace/security_audit.log
git commit -m "chore: automated audit refresh $(date +%Y-%m-%d_%H-%M-%S)"
git push origin main
echo "Audit completed, committed, and pushed successfully."
