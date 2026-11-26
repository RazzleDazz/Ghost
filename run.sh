#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCK_FILE="${TMPDIR:-/data/data/com.termux/files/usr/tmp}/ghost_agent.lock"
LOG_DIR="${AGENT_DIR}/logs"

mkdir -p "${LOG_DIR}"

exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
    echo "[SKIP] ghost_agent is already running (lock held: ${LOCK_FILE})" >&2
    exit 0
fi

# Close lock FD before replacing process image with python3
exec 9>&-

# Keep at most 50 timestamped JSON audit logs to conserve UFS flash storage
ls -1t "${LOG_DIR}"/audit_*.json 2>/dev/null | tail -n +51 | xargs -r rm -f

exec python3 "${AGENT_DIR}/agent.py" "$@"
