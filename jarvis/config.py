"""Central configuration for Jarvis.

Every value can be overridden with an environment variable, so the LaunchAgent
(or your shell) can retune Jarvis without editing code.
"""
import os
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")

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
# Full autonomy: "bypassPermissions" lets Jarvis act (update Notion, send email)
# without prompting — required since -p mode can't answer permission prompts.
# Dial back with "default" (refuses tools needing approval). See jarvis/README.md.
CLAUDE_PERMISSION_MODE = os.environ.get("JARVIS_PERMISSION_MODE", "bypassPermissions")
CLAUDE_TIMEOUT_S = float(os.environ.get("JARVIS_BRAIN_TIMEOUT", "120"))
CLAUDE_MODEL = os.environ.get("JARVIS_CLAUDE_MODEL", "")  # blank = CLI default

# --- Playbooks (domain knowledge the brain operates with) ------------------
PLAYBOOKS_DIR = JARVIS_DIR / "playbooks"
# Which playbooks to load as the brain's project memory (comma-separated).
ENABLED_PLAYBOOKS = [
    p.strip()
    for p in os.environ.get("JARVIS_PLAYBOOKS", "recruiting,mortgage").split(",")
    if p.strip()
]
# When ON, borrower/consumer messages are drafted for approval instead of sent.
# Default OFF (full autonomy). The lawful-conduct rules in the foundation
# (consent/DNC, no rate promises, fair lending) apply either way.
BORROWER_DRAFT_ONLY = _env_bool("JARVIS_BORROWER_DRAFT_ONLY", False)

# --- Conversation capture (Plaud recorder, mic notes, dropped audio) --------
# Drop an audio file or transcript here and Jarvis will transcribe it (if
# needed), summarize it, pull next steps, and log highlights to Notion. Point
# this at a cloud-synced folder (iCloud/Dropbox) that your Plaud exports into.
CAPTURE_INBOX_DIR = Path(os.environ.get("JARVIS_INBOX", Path.home() / "JarvisInbox"))
CAPTURE_WORKSPACE_DIR = WORKSPACE_DIR / "capture"  # isolated brain thread for capture
CAPTURE_POLL_S = float(os.environ.get("JARVIS_CAPTURE_POLL", "10"))
# Safety cap on a voice-triggered "take notes" session (default 2 hours).
CAPTURE_MAX_SESSION_S = float(os.environ.get("JARVIS_NOTE_MAX", "7200"))
# Speak the TL;DR aloud when a capture finishes processing.
CAPTURE_READBACK = _env_bool("JARVIS_CAPTURE_READBACK", True)

# --- On-screen HUD (the movie-style reactor) -------------------------------
# The voice loop serves a localhost page that animates with Jarvis's state.
# Open http://127.0.0.1:<port> fullscreen on the Mac mini's display.
HUD_ENABLED = _env_bool("JARVIS_HUD", True)
HUD_HOST = os.environ.get("JARVIS_HUD_HOST", "127.0.0.1")
HUD_PORT = int(os.environ.get("JARVIS_HUD_PORT", "8765"))
