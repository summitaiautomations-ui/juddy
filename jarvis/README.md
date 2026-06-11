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

## What it does for you

Jarvis runs two relationship pipelines out of your Notion workspace:

- **Recruiting** (B2B) — nurture loan officers / branch managers: intake, find
  who's due, draft re-engagement, log every touch.
- **Mortgage** (consumers) — stage-aware borrower follow-up and post-close
  nurture, plus the realtor referral drip. Borrower-facing messages are
  **drafted for your approval by default**, never auto-sent.

The brain's domain knowledge lives in editable playbooks under
[`playbooks/`](playbooks/) — `foundation.md` (the shared nurture loop +
guardrails), `recruiting.md`, `mortgage.md`, and `pipelines.json` (the real
Notion database IDs, stages, and field names). On startup these are compiled
into the brain's workspace as `CLAUDE.md`, so every call operates with your
actual schema. Edit the playbooks and restart to change behaviour.

## Conversation capture (Plaud, mic notes, dropped audio)

Jarvis can also **summarize your conversations and log highlights to Notion**.
A capture worker (`com.juddy.jarvis-capture`) watches an inbox folder; drop in
any audio file or transcript and it transcribes (faster-whisper), summarizes,
pulls next steps, and updates the matching pipeline record.

Three ways to feed it:

```bash
# 1. Just talk to Jarvis:
#    "Hey Jarvis, take notes"  ->  ...conversation...  ->  "Hey Jarvis, done"
#    It records, drops the audio in the inbox, and summarizes to Notion.

# 2. Record from the mic manually:
jarvis/.venv/bin/python -m jarvis.record        # Ctrl-C to stop
jarvis/.venv/bin/python -m jarvis.record 600    # cap at 600s

# 3. Drop any audio/transcript into the inbox (override with JARVIS_INBOX):
~/JarvisInbox/                                  # processed/ and failed/ created inside
```

**Plaud:** point `JARVIS_INBOX` at the cloud-synced folder your Plaud exports
into (iCloud/Dropbox), or just drop its `.m4a`/`.mp3`/transcript exports into
`~/JarvisInbox`. Anything that lands there gets processed and moved to
`processed/` (with a `.summary.md`) or `failed/`.

> Capture **records and logs only** — it never sends outbound messages. Mind
> recording-consent norms when capturing client conversations.

## Wiring the brain to Notion + Gmail (required for real work)

The MCP servers must be added to the **`claude` CLI on the Mac mini** (separate
from any web session). For example:

```bash
claude mcp add notion --transport http https://mcp.notion.com/mcp
claude mcp add gmail  ...   # your Gmail MCP endpoint
```

Until they're added, Jarvis can talk but can't read/update pipelines or draft
email. To let it take actions (draft/send, update Notion) unattended, also raise
`JARVIS_PERMISSION_MODE` (below).

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
| `JARVIS_PLAYBOOKS`        | `recruiting,mortgage` | which playbooks to load    |
| `JARVIS_BORROWER_DRAFT_ONLY` | `true`   | never auto-send to consumers         |
| `JARVIS_INBOX`            | `~/JarvisInbox` | capture inbox folder            |
| `JARVIS_CAPTURE_READBACK` | `true`      | speak the TL;DR after capture        |
