#!/usr/bin/env bash
# Reverse of install.sh: stop+remove the LaunchAgents and clear pmset overrides.
# Power settings are reset to defaults. Logs are kept.

set -uo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: macOS only" >&2
  exit 1
fi

LAUNCH_AGENTS="${HOME}/Library/LaunchAgents"
UID_NUM="$(id -u)"

remove_agent() {
  local label="$1"
  local plist="${LAUNCH_AGENTS}/${label}.plist"
  echo "==> removing ${label}"
  launchctl bootout "gui/${UID_NUM}/${label}" 2>/dev/null || true
  rm -f "${plist}"
}

remove_agent "com.juddy.claude-code"
remove_agent "com.juddy.jarvis"
remove_agent "com.juddy.jarvis-capture"
remove_agent "com.juddy.healthcheck"

echo "==> cancelling nightly restart"
sudo pmset repeat cancel || true

echo "==> resetting pmset to defaults"
sudo pmset -a sleep 1 disksleep 10 displaysleep 10 womp 0 autorestart 0 || true

echo "done. logs left in ~/Library/Logs/juddy (delete manually if you want)."
