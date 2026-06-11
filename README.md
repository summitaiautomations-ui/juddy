# juddy

Turn a Mac mini into an always-on home for Claude — and give it a voice.

## Components

- **[`jarvis/`](jarvis/)** — Jarvis, a voice assistant with Claude as its brain.
  Say *"Hey Jarvis"*, speak, and Claude answers out loud. Wake word and
  speech-to-text run locally; the brain is the `claude` CLI.

- **[`scripts/mac-mini-always-on/`](scripts/mac-mini-always-on/)** — the
  always-on bundle: power settings (never sleep, nightly restart, wake-on-LAN),
  plus LaunchAgents that keep `claude`, Jarvis, and a healthcheck running 24/7
  and restart them on crash.

## Quick start

```bash
bash jarvis/setup.sh                          # one-time: Jarvis env + models
bash scripts/mac-mini-always-on/install.sh    # power settings + all LaunchAgents
```

Uninstall with `bash scripts/mac-mini-always-on/uninstall.sh`. Logs live in
`~/Library/Logs/juddy/`.

> macOS only.
