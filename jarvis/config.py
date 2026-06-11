"""Central configuration for Jarvis.

Every value can be overridden with an environment variable, so the LaunchAgent
(or your shell) can retune Jarvis without editing code.
"""
import os
from pathlib import Path

# --- Paths -----------------------------------------------------------------
JARVIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = JARVIS_DIR.parent
# Claude (the brain) runs here so its conversation history is isolated from the
# interactive `com.juddy.claude-code` session that lives in the repo root.
WORKSPACE_DIR = Path(os.environ.get("JARVIS_WORKSPACE", JARVIS_DIR / "workspace"))
LOG_DIR = Path(os.environ.get("JARVIS_LOG_DIR", Path.home() / "Library/Logs/juddy"))

# --- Audio capture ---------------------------------------------------------
SAMPLE_RATE = 16000
FRAME_SAMPLES = 1280            # 80 ms at 16 kHz — openWakeWord's preferred chunk
INPUT_DEVICE = os.environ.get("JARVIS_INPUT_DEVICE")  # None/"" = system default mic

# --- Wake word -------------------------------------------------------------
WAKE_MODEL = os.environ.get("JARVIS_WAKE_MODEL", "hey_jarvis")  # bundled pretrained
WAKE_THRESHOLD = float(os.environ.get("JARVIS_WAKE_THRESHOLD", "0.5"))
WAKE_COOLDOWN_S = float(os.environ.get("JARVIS_WAKE_COOLDOWN", "2.0"))
WAKE_ACK = os.environ.get("JARVIS_WAKE_ACK", "Yes?")  # spoken right after the wake word

# --- Endpointing (deciding when the speaker has finished a command) ---------
VAD_START_RMS = float(os.environ.get("JARVIS_VAD_START_RMS", "0.012"))
VAD_SILENCE_S = float(os.environ.get("JARVIS_VAD_SILENCE", "0.8"))
VAD_MAX_S = float(os.environ.get("JARVIS_VAD_MAX", "15.0"))
VAD_START_TIMEOUT_S = float(os.environ.get("JARVIS_VAD_START_TIMEOUT", "5.0"))

# --- Speech-to-text (faster-whisper, local) --------------------------------
STT_MODEL = os.environ.get("JARVIS_STT_MODEL", "base.en")
STT_DEVICE = os.environ.get("JARVIS_STT_DEVICE", "cpu")
STT_COMPUTE_TYPE = os.environ.get("JARVIS_STT_COMPUTE", "int8")

# --- Text-to-speech (macOS `say`) ------------------------------------------
TTS_VOICE = os.environ.get("JARVIS_VOICE", "Daniel")  # British male — fitting for Jarvis
TTS_RATE = os.environ.get("JARVIS_TTS_RATE", "")      # words/min; blank = system default

# --- Brain (the `claude` CLI in non-interactive mode) ----------------------
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
# "default" refuses tools that need approval (safe). Set to "acceptEdits" or
# "bypassPermissions" to let Jarvis actually take actions. See jarvis/README.md.
CLAUDE_PERMISSION_MODE = os.environ.get("JARVIS_PERMISSION_MODE", "default")
CLAUDE_TIMEOUT_S = float(os.environ.get("JARVIS_BRAIN_TIMEOUT", "120"))
CLAUDE_MODEL = os.environ.get("JARVIS_CLAUDE_MODEL", "")  # blank = CLI default
