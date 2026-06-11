#!/usr/bin/env bash
# One-shot installer that wires up:
#   1. pmset power settings (never sleep, nightly restart, wake-on-LAN, ...)
#   2. LaunchAgent that auto-starts `claude` in this repo, restarts on crash
#   3. LaunchAgent for Jarvis, the always-on voice assistant
#   4. LaunchAgent that runs healthcheck.sh every 5 minutes
#
# Re-runnable. Run from the repo root or anywhere -- it resolves its own path.
#
# Skip the Jarvis voice assistant with: SKIP_JARVIS=1 ./install.sh

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

# Jarvis voice assistant: its venv is created by jarvis/setup.sh.
JARVIS_PYTHON="${REPO_ROOT}/jarvis/.venv/bin/python"
INSTALL_JARVIS=1
if [[ "${SKIP_JARVIS:-0}" == "1" ]]; then
  INSTALL_JARVIS=0
elif [[ ! -x "${JARVIS_PYTHON}" ]]; then
  echo "==> jarvis venv missing; running jarvis/setup.sh"
  bash "${REPO_ROOT}/jarvis/setup.sh"
fi

echo "==> repo root      : ${REPO_ROOT}"
echo "==> user           : ${USER_NAME}"
echo "==> claude binary  : ${CLAUDE_BIN}"
echo "==> jarvis python  : ${JARVIS_PYTHON}"
echo "==> launch agents  : ${LAUNCH_AGENTS}"
echo "==> log directory  : ${LOG_DIR}"
echo

mkdir -p "${LAUNCH_AGENTS}" "${LOG_DIR}"
chmod +x "${SCRIPT_DIR}/power-settings.sh" "${SCRIPT_DIR}/healthcheck.sh"

render_plist() {
  local template="$1" dest="$2"
  sed \
    -e "s|__USER__|${USER_NAME}|g" \
    -e "s|__REPO__|${REPO_ROOT}|g" \
    -e "s|__CLAUDE_BIN__|${CLAUDE_BIN}|g" \
    -e "s|__JARVIS_PYTHON__|${JARVIS_PYTHON}|g" \
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

if [[ "${INSTALL_JARVIS}" == "1" && -x "${JARVIS_PYTHON}" ]]; then
  install_agent "com.juddy.jarvis" "${SCRIPT_DIR}/com.juddy.jarvis.plist.template"
  install_agent "com.juddy.jarvis-capture" "${SCRIPT_DIR}/com.juddy.jarvis-capture.plist.template"
else
  echo "==> skipping com.juddy.jarvis (no venv; run jarvis/setup.sh then re-run)"
fi

install_agent "com.juddy.healthcheck" "${SCRIPT_DIR}/com.juddy.healthcheck.plist.template"

echo
echo "==> applying power settings (will prompt for sudo)"
sudo "${SCRIPT_DIR}/power-settings.sh"

cat <<EOF

==========================================================================
  install complete.

  inspect the agents:
    launchctl print gui/$(id -u)/com.juddy.claude-code
    launchctl print gui/$(id -u)/com.juddy.jarvis
    launchctl print gui/$(id -u)/com.juddy.jarvis-capture
    launchctl print gui/$(id -u)/com.juddy.healthcheck

  tail the logs:
    tail -f "${LOG_DIR}"/claude-code.{out,err}.log
    tail -f "${LOG_DIR}"/jarvis.log
    tail -f "${LOG_DIR}"/jarvis-capture.log
    tail -f "${LOG_DIR}"/healthcheck.log

  uninstall:
    bash "${SCRIPT_DIR}/uninstall.sh"
==========================================================================
EOF
