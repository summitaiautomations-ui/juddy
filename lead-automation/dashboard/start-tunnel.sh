#!/bin/bash
# Dashboard server launcher + Cloudflare tunnel watchdog.
# Run from cron every ~5 min; restarts whichever piece is down.

set -e

DASHBOARD_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$(cd "$DASHBOARD_DIR/.." && pwd)"
LOG_DIR="$BASE_DIR"
PORT="${DASHBOARD_PORT:-18790}"

if ! pgrep -f "server.py $PORT" > /dev/null 2>&1; then
    cd "$DASHBOARD_DIR"
    nohup python3 server.py "$PORT" >> "$LOG_DIR/dashboard_server.log" 2>&1 &
    echo "$(date): Dashboard server started (PID $!)" >> "$LOG_DIR/dashboard_server.log"
fi

if ! pgrep -f "cloudflared.*tunnel run" > /dev/null 2>&1; then
    if command -v sudo > /dev/null 2>&1; then
        sudo service cloudflared start || true
    else
        service cloudflared start || true
    fi
    echo "$(date): Restarted cloudflared service" >> "$LOG_DIR/dashboard_server.log"
fi
