#!/usr/bin/env bash
# Removes the Quo -> Notion sync LaunchAgent. Leaves config and state in place.
set -euo pipefail

LABEL="com.juddy.quo-notion-sync"
PLIST="${HOME}/Library/LaunchAgents/${LABEL}.plist"

launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
rm -f "${PLIST}"
echo "removed ${LABEL}."
echo "config kept at ~/.config/juddy/quo-notion-sync.json"
echo "state kept at  ~/.local/state/juddy/quo-notion-sync/state.json"
