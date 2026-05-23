#!/usr/bin/env bash
# Serves the recruiting dashboard on a local port and syncs drag-and-drop
# stage changes back to Notion. Kept alive by launchd
# (see com.juddy.dashboard-serve.plist.template).
#
# Open the dashboard at:  http://localhost:8800/
# Requires NOTION_TOKEN in the environment for the drag-to-Notion sync.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASH_DIR="$(cd "${SCRIPT_DIR}/../../dashboard" && pwd)"

cd "${DASH_DIR}" || { echo "ERROR: dashboard dir not found"; exit 1; }

exec node server.mjs
