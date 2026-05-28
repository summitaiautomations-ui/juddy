#!/usr/bin/env bash
# Double-click ONCE to make the dashboard run in the background forever.
# After this, http://localhost:8800 is always live -- no Terminal needed.
#
# To remove later, double-click Uninstall-Always-On.command.

set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

# Make sure common Node install locations are on PATH (Homebrew, system, nvm).
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.nvm/versions/node:$PATH"
NODE_BIN="$(command -v node || true)"

if [ -z "$NODE_BIN" ]; then
  echo
  echo "============================================================"
  echo "  ERROR: Node.js is not installed."
  echo
  echo "  Install it from:"
  echo "    https://nodejs.org/en/download"
  echo
  echo "  Then run this installer again."
  echo "============================================================"
  echo
  read -n 1 -s -r -p "Press any key to close..."
  exit 1
fi

LABEL="com.juddy.dashboard-serve"
AGENTS="$HOME/Library/LaunchAgents"
PLIST="$AGENTS/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs/juddy"
mkdir -p "$AGENTS" "$LOG_DIR"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$NODE_BIN</string>
        <string>$HERE/server.mjs</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$HERE</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>DASHBOARD_PORT</key>
        <string>8800</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/dashboard-serve.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/dashboard-serve.log</string>
</dict>
</plist>
EOF

# Reload cleanly (handles a re-install).
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl enable "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl kickstart -k "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true

sleep 2
open "http://localhost:8800" 2>/dev/null || true

echo
echo "============================================================"
echo "  Done! The dashboard is now always running at:"
echo "      http://localhost:8800"
echo
echo "  It will start automatically every time you log in."
echo "  Bookmark that URL and open it whenever you want."
echo
echo "  Logs:    $LOG_DIR/dashboard-serve.log"
echo "  Remove:  double-click Uninstall-Always-On.command"
echo "============================================================"
echo
read -n 1 -s -r -p "Press any key to close this window..."
echo
