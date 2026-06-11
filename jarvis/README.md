# Jarvis

An always-on voice assistant for the Mac mini, with **Claude as its brain**.

```
mic → "Hey Jarvis" → record until you stop → speech-to-text → Claude → speech
```

Everything except Claude runs locally on the machine:

| Stage        | Implementation                                  |
|--------------|-------------------------------------------------|
| Wake word    | [openWakeWord](https://github.com/dscripka/openWakeWord) — bundled `hey_jarvis` model |
| Speech-to-text | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (`base.en`, on-device) |
| Brain        | the `claude` CLI in `-p` mode (reuses this machine's auth + agent tools) |
| Text-to-speech | macOS `say` (voice: `Daniel`)                 |

## Setup

```bash
bash jarvis/setup.sh          # creates jarvis/.venv, installs deps, downloads models
jarvis/.venv/bin/python -m jarvis   # run it; then say "Hey Jarvis"
```

`setup.sh` installs PortAudio via Homebrew if it's missing. The first run
downloads the wake-word and Whisper models.

> **Microphone permission:** macOS gates mic access. The first interactive run
> shows a prompt. If Jarvis runs headless under launchd and never prompts,
> grant mic access to `jarvis/.venv/bin/python` under
> *System Settings → Privacy & Security → Microphone*.

## Running always-on

Jarvis installs as the `com.juddy.jarvis` LaunchAgent alongside `claude-code`:

```bash
bash scripts/mac-mini-always-on/install.sh     # installs jarvis too
SKIP_JARVIS=1 bash scripts/mac-mini-always-on/install.sh   # skip jarvis
```

Logs land in `~/Library/Logs/juddy/jarvis.log` (and `jarvis.{out,err}.log`).
The healthcheck reports the `jarvis` job state every 5 minutes.

## How the brain is wired

`brain.py` shells out to `claude -p "<what you said>" --output-format json`,
running in an isolated `jarvis/workspace/` directory and using `--continue` to
keep the conversation going. Because it's the same `claude` CLI the always-on
setup already authenticates, Jarvis inherits your login and the full agent
toolset (files, MCP servers, etc.) for free — no separate API key.

By default the permission mode is `default`, so Claude will **not** run tools
that need approval (it can't prompt you by voice). To let Jarvis actually take
actions, raise the permission level — be deliberate, this lets it act
unattended:

```bash
# in the LaunchAgent env or your shell
export JARVIS_PERMISSION_MODE=acceptEdits      # or bypassPermissions for full autonomy
```

## Configuration

Everything is tunable via environment variables (see `config.py`). Common ones:

| Variable                  | Default     | Purpose                              |
|---------------------------|-------------|--------------------------------------|
| `JARVIS_WAKE_THRESHOLD`   | `0.5`       | wake sensitivity (lower = touchier)  |
| `JARVIS_STT_MODEL`        | `base.en`   | Whisper model (`tiny.en`…`small.en`) |
| `JARVIS_VOICE`            | `Daniel`    | macOS `say` voice (`say -v ?`)       |
| `JARVIS_PERMISSION_MODE`  | `default`   | Claude tool permissions              |
| `JARVIS_CLAUDE_MODEL`     | CLI default | pin a specific model                 |
| `JARVIS_INPUT_DEVICE`     | system mic  | input device name or index           |
