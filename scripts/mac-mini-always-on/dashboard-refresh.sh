#!/usr/bin/env bash
# Regenerates the recruiting dashboard data from Notion.
# Run via launchd every 15 min (see com.juddy.dashboard-refresh.plist.template).
#
# Requires NOTION_TOKEN in the environment (set it in the plist, or below).

set -uo pipefail

LOG_DIR="${HOME}/Library/Logs/juddy"
mkdir -p "${LOG_DIR}"

ts() { date "+%Y-%m-%d %H:%M:%S"; }

# Resolve the dashboard dir relative to this script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASH_DIR="$(cd "${SCRIPT_DIR}/../../dashboard" && pwd)"

# Uncomment and set if you prefer not to put the token in the plist:
# export NOTION_TOKEN="ntn_xxx"

if [[ -z "${NOTION_TOKEN:-}" ]]; then
  echo "[$(ts)] ERROR: NOTION_TOKEN not set; skipping refresh."
  exit 1
fi

cd "${DASH_DIR}" || { echo "[$(ts)] ERROR: dashboard dir not found"; exit 1; }

if node refresh.mjs; then
  echo "[$(ts)] dashboard data refreshed."
else
  echo "[$(ts)] ERROR: refresh.mjs failed."
  exit 1
fi
