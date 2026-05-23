#!/usr/bin/env bash
# Double-click this file in Finder to launch the live recruiting dashboard.
# It starts the local server and opens the dashboard in your browser.
#
# For drag-to-Notion sync, put your token in a file next to this one named
# ".env" containing:   NOTION_TOKEN=ntn_xxx

cd "$(dirname "$0")" || exit 1

# Load NOTION_TOKEN from .env if present.
if [ -f .env ]; then
  set -a; . ./.env; set +a
fi

PORT="${DASHBOARD_PORT:-8800}"
echo "Starting dashboard on http://localhost:${PORT} …"
( sleep 1; open "http://localhost:${PORT}" ) &
exec node server.mjs
