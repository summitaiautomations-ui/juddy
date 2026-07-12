#!/usr/bin/env bash
# Triggered by launchd whenever a file lands in ~/Downloads -- i.e. every time
# you AirDrop something to the Mac mini (see com.juddy.disc-airdrop.plist.template).
# Sweeps new photos into the pipeline, identifies them with Claude, and pushes.
# Logs to ~/Library/Logs/juddy/disc-pics.log.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${HOME}/Library/Logs/juddy"
mkdir -p "${LOG_DIR}"
exec >> "${LOG_DIR}/disc-pics.log" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Downloads changed (AirDrop?), running airdrop import + catalog"

# Let the AirDrop transfer finish writing before we touch anything.
sleep 3

bash "${SCRIPT_DIR}/airdrop-import.sh"   # sweeps Downloads -> inbox, cleaned up
bash "${SCRIPT_DIR}/catalog.sh"          # identifies inbox -> disc-pics-data/incoming/
bash "${SCRIPT_DIR}/sync.sh"             # pushes them (additive-only, never conflicts)
# The mini stops here. Fold staged discs into the storefront from one place
# (assigns ids, reconciles dictated details) with:  python3 merge-incoming.py
