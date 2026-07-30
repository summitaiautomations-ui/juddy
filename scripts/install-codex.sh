#!/usr/bin/env bash
# Install the OpenAI Codex CLI (the `codex` command).
#
# Strategy, in order of preference:
#   1. Homebrew  -> `brew install codex`           (macOS / Linuxbrew)
#   2. npm       -> `npm install -g @openai/codex`  (anywhere Node is present)
#
# Idempotent: re-running upgrades an existing install rather than failing.
# Override the method with CODEX_INSTALL_METHOD=brew|npm ./install-codex.sh

set -euo pipefail

NPM_PKG="@openai/codex"
METHOD="${CODEX_INSTALL_METHOD:-auto}"

have() { command -v "$1" >/dev/null 2>&1; }

install_with_brew() {
  echo "==> installing codex via Homebrew"
  if have codex && brew list codex >/dev/null 2>&1; then
    brew upgrade codex
  else
    brew install codex
  fi
}

install_with_npm() {
  echo "==> installing ${NPM_PKG} via npm (global)"
  npm install -g "${NPM_PKG}"
}

case "${METHOD}" in
  brew)
    have brew || { echo "error: CODEX_INSTALL_METHOD=brew but Homebrew is not installed" >&2; exit 1; }
    install_with_brew
    ;;
  npm)
    have npm || { echo "error: CODEX_INSTALL_METHOD=npm but npm is not installed" >&2; exit 1; }
    install_with_npm
    ;;
  auto)
    if have brew; then
      install_with_brew
    elif have npm; then
      install_with_npm
    else
      cat >&2 <<'EOF'
error: need either Homebrew or npm to install the Codex CLI.

  macOS : install Homebrew  -> https://brew.sh
  any   : install Node.js   -> https://nodejs.org  (gives you npm)

then re-run this script.
EOF
      exit 1
    fi
    ;;
  *)
    echo "error: CODEX_INSTALL_METHOD must be one of: auto, brew, npm (got '${METHOD}')" >&2
    exit 1
    ;;
esac

echo
if have codex; then
  echo "==> codex installed: $(command -v codex)"
  codex --version || true
  echo
  echo "next: run 'codex' in a project, or 'codex login' to authenticate."
else
  echo "warning: install finished but 'codex' is not on PATH yet." >&2
  echo "open a new shell, or ensure your npm global bin / Homebrew bin is on PATH." >&2
  exit 1
fi
