#!/usr/bin/env bash
# Serves the recruiting dashboard on a local port so an open browser tab can
# live-poll data.json (every 15 min). Kept alive by launchd
# (see com.juddy.dashboard-serve.plist.template).
#
# Open the dashboard at:  http://localhost:8800/

set -uo pipefail

PORT="${DASHBOARD_PORT:-8800}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASH_DIR="$(cd "${SCRIPT_DIR}/../../dashboard" && pwd)"

# Bind to localhost only — this is a personal dashboard, not a public site.
exec python3 -m http.server "${PORT}" --bind 127.0.0.1 --directory "${DASH_DIR}"
