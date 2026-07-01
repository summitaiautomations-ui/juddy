#!/usr/bin/env bash
# Triggered by launchd whenever Photo Booth saves a new photo (see
# com.juddy.disc-pics.plist.template). Imports new photos, then catalogs
# them with Claude. Logs to ~/Library/Logs/juddy/disc-pics.log.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${HOME}/Library/Logs/juddy"
mkdir -p "${LOG_DIR}"
exec >> "${LOG_DIR}/disc-pics.log" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] photo booth changed, running import + catalog"

# Give Photo Booth a moment to finish writing the file it just saved.
sleep 3

bash "${SCRIPT_DIR}/import.sh"
bash "${SCRIPT_DIR}/catalog.sh"
python3 "${SCRIPT_DIR}/listings.py" || echo "warn: listings generation failed, syncing anyway"
bash "${SCRIPT_DIR}/sync.sh"
