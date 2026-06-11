#!/usr/bin/env bash
# Set up Jarvis's Python environment: a virtualenv, dependencies, and
# pre-downloaded models so the first wake word doesn't stall.
#
# Re-runnable. macOS only (uses CoreAudio via PortAudio and the `say` command).
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: Jarvis runs on macOS only" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${SCRIPT_DIR}/.venv"
PY="${PYTHON_BIN:-python3}"

echo "==> python: $("${PY}" --version 2>&1) ($(command -v "${PY}"))"

# sounddevice needs PortAudio. Install it via Homebrew if it's missing.
if [[ ! -e /opt/homebrew/lib/libportaudio.dylib && ! -e /usr/local/lib/libportaudio.dylib ]]; then
  if command -v brew >/dev/null 2>&1; then
    echo "==> installing portaudio via Homebrew"
    brew install portaudio
  else
    echo "warning: portaudio not found and Homebrew is unavailable."
    echo "         install it manually or 'pip install sounddevice' may fail."
  fi
fi

echo "==> creating virtualenv at ${VENV}"
"${PY}" -m venv "${VENV}"
# shellcheck disable=SC1091
source "${VENV}/bin/activate"

echo "==> upgrading pip"
pip install --quiet --upgrade pip wheel

echo "==> installing python dependencies"
pip install --quiet -r "${SCRIPT_DIR}/requirements.txt"

echo "==> pre-downloading wake-word models (openWakeWord)"
python - <<'PY'
import openwakeword.utils as u
u.download_models()
print("   wake-word models ready")
PY

echo "==> warming up the speech-to-text model (faster-whisper)"
JARVIS_STT_MODEL="${JARVIS_STT_MODEL:-base.en}" python - <<'PY'
import os
from faster_whisper import WhisperModel
model = os.environ.get("JARVIS_STT_MODEL", "base.en")
WhisperModel(model, device="cpu", compute_type="int8")
print(f"   STT model '{model}' downloaded")
PY

cat <<EOF

==========================================================================
  Jarvis environment ready.

  Try it interactively (then say "Hey Jarvis"):
    "${VENV}/bin/python" -m jarvis

  Install it as an always-on LaunchAgent (alongside claude-code):
    bash "${SCRIPT_DIR}/../scripts/mac-mini-always-on/install.sh"

  NOTE: macOS will prompt for microphone access the first time. If Jarvis
  runs headless under launchd and never gets a prompt, grant mic access to
  the python binary at:
    ${VENV}/bin/python
  in System Settings > Privacy & Security > Microphone.
==========================================================================
EOF
