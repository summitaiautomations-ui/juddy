#!/usr/bin/env bash
# One-shot installer that wires up:
#   1. pmset power settings (never sleep, nightly restart, wake-on-LAN, ...)
#   2. LaunchAgent that auto-starts `claude` in this repo, restarts on crash
#   3. LaunchAgent that runs healthcheck.sh every 5 minutes
#   4. LaunchAgent that refreshes the recruiting dashboard from Notion (15 min)
#   5. LaunchAgent that serves the dashboard at http://localhost:8800
#
# Re-runnable. Run from the repo root or anywhere -- it resolves its own path.
#
# For the dashboard refresh job, set your Notion integration token first:
#   NOTION_TOKEN=ntn_xxx ./install.sh

set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: this installer only runs on macOS" >&2
  exit 1
fi
if [[ $EUID -eq 0 ]]; then
  echo "error: do not run this as root. it will sudo where needed." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
USER_NAME="$(id -un)"
LAUNCH_AGENTS="${HOME}/Library/LaunchAgents"
LOG_DIR="${HOME}/Library/Logs/juddy"

# Locate the claude CLI. Allow override: CLAUDE_BIN=/path/to/claude ./install.sh
CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || true)}"
if [[ -z "${CLAUDE_BIN}" ]]; then
  echo "error: cannot find 'claude' on PATH. set CLAUDE_BIN=/path/to/claude and re-run." >&2
  exit 1
fi

# Notion token for the dashboard refresh job. Optional at install time --
# the refresh job will simply skip until a token is present.
NOTION_TOKEN="${NOTION_TOKEN:-}"

echo "==> repo root      : ${REPO_ROOT}"
echo "==> user           : ${USER_NAME}"
echo "==> claude binary  : ${CLAUDE_BIN}"
echo "==> launch agents  : ${LAUNCH_AGENTS}"
echo "==> log directory  : ${LOG_DIR}"
if [[ -n "${NOTION_TOKEN}" ]]; then
  echo "==> notion token   : set (dashboard refresh enabled)"
else
  echo "==> notion token   : NOT set -- dashboard refresh will skip until you"
  echo "                     re-run with NOTION_TOKEN=ntn_xxx ./install.sh"
fi
echo

mkdir -p "${LAUNCH_AGENTS}" "${LOG_DIR}"
chmod +x "${SCRIPT_DIR}/power-settings.sh" "${SCRIPT_DIR}/healthcheck.sh" \
  "${SCRIPT_DIR}/dashboard-refresh.sh" "${SCRIPT_DIR}/dashboard-serve.sh"

render_plist() {
  local template="$1" dest="$2"
  sed \
    -e "s|__USER__|${USER_NAME}|g" \
    -e "s|__REPO__|${REPO_ROOT}|g" \
    -e "s|__CLAUDE_BIN__|${CLAUDE_BIN}|g" \
    -e "s|__NOTION_TOKEN__|${NOTION_TOKEN}|g" \
    "${template}" > "${dest}"
}

install_agent() {
  local label="$1" template="$2"
  local dest="${LAUNCH_AGENTS}/${label}.plist"
  echo "==> installing ${label}"
  # Bootout first so we always pick up edits to the plist.
  launchctl bootout "gui/$(id -u)/${label}" 2>/dev/null || true
  render_plist "${template}" "${dest}"
  launchctl bootstrap "gui/$(id -u)" "${dest}"
  launchctl enable "gui/$(id -u)/${label}"
  launchctl kickstart -k "gui/$(id -u)/${label}" || true
}

install_agent "com.juddy.claude-code" "${SCRIPT_DIR}/com.juddy.claude-code.plist.template"
install_agent "com.juddy.healthcheck" "${SCRIPT_DIR}/com.juddy.healthcheck.plist.template"
install_agent "com.juddy.dashboard-refresh" "${SCRIPT_DIR}/com.juddy.dashboard-refresh.plist.template"
install_agent "com.juddy.dashboard-serve" "${SCRIPT_DIR}/com.juddy.dashboard-serve.plist.template"

echo
echo "==> applying power settings (will prompt for sudo)"
sudo "${SCRIPT_DIR}/power-settings.sh"

cat <<EOF

==========================================================================
  install complete.

  the recruiting dashboard is now live at:
    http://localhost:8800

  inspect the agents:
    launchctl print gui/$(id -u)/com.juddy.claude-code
    launchctl print gui/$(id -u)/com.juddy.healthcheck
    launchctl print gui/$(id -u)/com.juddy.dashboard-refresh
    launchctl print gui/$(id -u)/com.juddy.dashboard-serve

  tail the logs:
    tail -f "${LOG_DIR}"/claude-code.{out,err}.log
    tail -f "${LOG_DIR}"/healthcheck.log
    tail -f "${LOG_DIR}"/dashboard-refresh.log
    tail -f "${LOG_DIR}"/dashboard-serve.log

  uninstall:
    bash "${SCRIPT_DIR}/uninstall.sh"
==========================================================================
EOF
