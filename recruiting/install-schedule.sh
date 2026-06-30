#!/usr/bin/env bash
# Install the daily recruiting-digest LaunchAgent (fires every morning).
#
#   bash recruiting/install-schedule.sh           # default 7:00 AM
#   DIGEST_HOUR=6 DIGEST_MINUTE=30 bash recruiting/install-schedule.sh
#
# Re-runnable. Run from anywhere -- it resolves its own path. Uninstall:
#   launchctl bootout "gui/$(id -u)/com.juddy.recruiting-digest"
#   rm ~/Library/LaunchAgents/com.juddy.recruiting-digest.plist

set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: this installer only runs on macOS" >&2
  exit 1
fi
if [[ $EUID -eq 0 ]]; then
  echo "error: do not run this as root." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
USER_NAME="$(id -un)"
LABEL="com.juddy.recruiting-digest"
LAUNCH_AGENTS="${HOME}/Library/LaunchAgents"
LOG_DIR="${HOME}/Library/Logs/juddy"
DEST="${LAUNCH_AGENTS}/${LABEL}.plist"

HOUR="${DIGEST_HOUR:-7}"
MINUTE="${DIGEST_MINUTE:-0}"

VENV_PY="${REPO_ROOT}/recruiting/.venv/bin/python"
if [[ ! -x "${VENV_PY}" ]]; then
  echo "error: ${VENV_PY} not found." >&2
  echo "       create it first:" >&2
  echo "         python3 -m venv recruiting/.venv" >&2
  echo "         recruiting/.venv/bin/pip install -r recruiting/requirements.txt" >&2
  exit 1
fi

echo "==> repo root   : ${REPO_ROOT}"
echo "==> schedule    : daily at ${HOUR}:$(printf '%02d' "${MINUTE}")"
echo "==> python      : ${VENV_PY}"
echo "==> log         : ${LOG_DIR}/recruiting-digest.log"
echo

mkdir -p "${LAUNCH_AGENTS}" "${LOG_DIR}"

sed \
  -e "s|__USER__|${USER_NAME}|g" \
  -e "s|__REPO__|${REPO_ROOT}|g" \
  -e "s|__HOUR__|${HOUR}|g" \
  -e "s|__MINUTE__|${MINUTE}|g" \
  "${SCRIPT_DIR}/${LABEL}.plist.template" > "${DEST}"

# Bootout first so edits to the plist always take effect.
launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "${DEST}"
launchctl enable "gui/$(id -u)/${LABEL}"

echo "==> installed ${LABEL}"
echo
echo "send one right now to test:"
echo "    launchctl kickstart -k \"gui/$(id -u)/${LABEL}\""
echo "inspect / tail:"
echo "    launchctl print gui/$(id -u)/${LABEL}"
echo "    tail -f \"${LOG_DIR}/recruiting-digest.log\""
