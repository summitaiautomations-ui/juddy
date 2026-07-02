#!/usr/bin/env bash
# Installs the Quo -> Notion sync as a LaunchAgent that runs every 5 minutes.
#
# Prereqs (see README.md):
#   1. ~/.config/juddy/quo-notion-sync.json filled in with your API keys
#      (this script seeds it from config.example.json if missing)
#   2. The Notion databases shared with your Notion integration
#
# Re-runnable. Run from anywhere -- it resolves its own path.

set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: this installer only runs on macOS" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
USER_NAME="$(id -un)"
LAUNCH_AGENTS="${HOME}/Library/LaunchAgents"
LOG_DIR="${HOME}/Library/Logs/juddy"
CONFIG_DIR="${HOME}/.config/juddy"
CONFIG="${CONFIG_DIR}/quo-notion-sync.json"
LABEL="com.juddy.quo-notion-sync"

PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || true)}"
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "error: python3 not found. Install Xcode Command Line Tools: xcode-select --install" >&2
  exit 1
fi

mkdir -p "${LAUNCH_AGENTS}" "${LOG_DIR}" "${CONFIG_DIR}"
chmod +x "${SCRIPT_DIR}/sync.py"

if [[ ! -f "${CONFIG}" ]]; then
  cp "${SCRIPT_DIR}/config.example.json" "${CONFIG}"
  chmod 600 "${CONFIG}"
  echo "==> created ${CONFIG}"
  echo "    EDIT IT NOW: add your Quo API key and Notion integration token,"
  echo "    then re-run this installer."
  exit 0
fi

if grep -q "YOUR_" "${CONFIG}"; then
  echo "error: ${CONFIG} still contains placeholder values. Fill in your keys first." >&2
  exit 1
fi
chmod 600 "${CONFIG}"

echo "==> repo root  : ${REPO_ROOT}"
echo "==> python     : ${PYTHON_BIN}"
echo "==> config     : ${CONFIG}"

echo "==> test run (dry run)"
"${PYTHON_BIN}" "${SCRIPT_DIR}/sync.py" --dry-run --verbose

DEST="${LAUNCH_AGENTS}/${LABEL}.plist"
echo "==> installing ${LABEL}"
launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
sed \
  -e "s|__USER__|${USER_NAME}|g" \
  -e "s|__REPO__|${REPO_ROOT}|g" \
  -e "s|__PYTHON__|${PYTHON_BIN}|g" \
  "${SCRIPT_DIR}/${LABEL}.plist.template" > "${DEST}"
launchctl bootstrap "gui/$(id -u)" "${DEST}"
launchctl enable "gui/$(id -u)/${LABEL}"
launchctl kickstart -k "gui/$(id -u)/${LABEL}" || true

cat <<EOF

==========================================================================
  install complete. The sync now runs every 5 minutes.

  tail the logs:
    tail -f "${LOG_DIR}/quo-notion-sync.log"

  run once by hand:
    ${PYTHON_BIN} ${SCRIPT_DIR}/sync.py --verbose

  uninstall:
    bash "${SCRIPT_DIR}/uninstall.sh"
==========================================================================
EOF
