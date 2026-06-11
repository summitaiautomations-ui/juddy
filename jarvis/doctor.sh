#!/usr/bin/env bash
# Jarvis preflight "doctor" — checks that everything needed to run Jarvis on
# this Mac mini is in place, and points at whatever's missing.
#
# Safe to run any time:  bash jarvis/doctor.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PY="${SCRIPT_DIR}/.venv/bin/python"
UID_NUM="$(id -u)"

fails=0
warns=0
ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
warn() { printf "  \033[33m!\033[0m %s\n" "$1"; warns=$((warns + 1)); }
bad()  { printf "  \033[31m✗\033[0m %s\n" "$1"; fails=$((fails + 1)); }

echo "Jarvis preflight"
echo "================"

# --- Platform --------------------------------------------------------------
echo "Platform"
if [[ "$(uname -s)" == "Darwin" ]]; then
  ok "macOS ($(sw_vers -productVersion 2>/dev/null || echo '?'))"
else
  bad "not macOS — Jarvis runs on macOS only"
fi

# --- Claude CLI (the brain) ------------------------------------------------
echo "Brain"
CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || true)}"
if [[ -n "${CLAUDE_BIN}" ]]; then
  ok "claude CLI: ${CLAUDE_BIN} ($("${CLAUDE_BIN}" --version 2>/dev/null || echo '?'))"
else
  bad "claude CLI not found on PATH (set CLAUDE_BIN=/path/to/claude)"
fi

# --- Python environment ----------------------------------------------------
echo "Voice environment"
if [[ -x "${VENV_PY}" ]]; then
  ok "venv: ${VENV_PY}"
  if "${VENV_PY}" - <<'PY' 2>/dev/null
import importlib
for m in ("sounddevice", "numpy", "openwakeword", "faster_whisper"):
    importlib.import_module(m)
PY
  then
    ok "python deps import (sounddevice, numpy, openwakeword, faster-whisper)"
  else
    bad "python deps failed to import — run jarvis/setup.sh"
  fi
else
  bad "venv missing — run jarvis/setup.sh"
fi

# --- MCP servers (so the brain can act) ------------------------------------
echo "MCP servers (for Notion / Gmail)"
if [[ -n "${CLAUDE_BIN}" ]]; then
  mcp_list="$("${CLAUDE_BIN}" mcp list 2>/dev/null || true)"
  if grep -qi "notion" <<<"${mcp_list}"; then ok "notion configured"; else warn "notion not configured — run jarvis/wire-mcp.sh"; fi
  if grep -qi "gmail"  <<<"${mcp_list}"; then ok "gmail configured";  else warn "gmail not configured — see jarvis/wire-mcp.sh"; fi
else
  warn "skipped (no claude CLI)"
fi

# --- Capture inbox ---------------------------------------------------------
echo "Capture"
INBOX="${JARVIS_INBOX:-${HOME}/JarvisInbox}"
if [[ -d "${INBOX}" ]]; then ok "inbox: ${INBOX}"; else warn "inbox ${INBOX} will be created on first run"; fi

# --- LaunchAgents ----------------------------------------------------------
echo "Always-on agents"
for label in com.juddy.jarvis com.juddy.jarvis-capture; do
  if launchctl print "gui/${UID_NUM}/${label}" >/dev/null 2>&1; then
    ok "${label} loaded"
  else
    warn "${label} not loaded — run scripts/mac-mini-always-on/install.sh"
  fi
done

# --- Reminders we can't auto-check -----------------------------------------
echo "Manual checks"
warn "microphone permission: grant ${VENV_PY} access under System Settings > Privacy & Security > Microphone"
warn "run '${CLAUDE_BIN:-claude} mcp' once and complete OAuth for Notion/Gmail if prompted"

echo
echo "Summary: ${fails} failed, ${warns} warnings"
if [[ ${fails} -gt 0 ]]; then
  echo "Not ready — resolve the ✗ items above."
  exit 1
fi
echo "Core looks good. Address any ! warnings for full functionality."
