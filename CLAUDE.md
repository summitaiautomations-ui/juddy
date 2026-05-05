# juddy

Justin's lead-automation + always-on Mac mini stack. The repo has no `main`
branch yet — work is split across feature branches that have not been merged.

## Where things live (by branch)

- **`claude/lead-nurture-workflow-LIHB9`** — Python lead-nurture / SMS engine.
  - `lead-automation/sms.py` — **the only place that should call the
    SimpleTexting send endpoint.** Exports `send_sms_once(config, to_phone,
    message, *, source, dedupe_namespace="")` which writes to
    `sms_ledger.json` before returning. Dedupe is fuzzy on purpose:
    (1) normalize emoji + whitespace + case before hashing, so two
    welcomes that differ only by a trailing 😊 are treated as the same
    text; (2) split each message into substantial sentences (>= 40 chars)
    and block if any sentence has already been sent to this number, so
    two market-update texts that share a closing paragraph won't both
    fire. Pass `dedupe_namespace="year:2026"` etc. when a template is
    intentionally recurring (birthdays).
  - `lead-automation/nurture_engine.py` — daemon. Loops every 60s, calls
    `check_inbound_deactivation`, `process_contacts`, periodic
    `check_demotions`. Sends via `sms.send_sms_once`. `process_contacts`
    persists `completed_steps` immediately after each send (not at end of
    tick) so a mid-tick crash can't re-enqueue an already-sent step.
  - `lead-automation/nurture_tracks.json` — track definitions: `hot`, `warm`,
    `cold`, `active_preapproval`, `past_client`. Each step has
    `id` / `delay_seconds` / `channel` (`sms` or `nudge`) / `message`.
  - `lead-automation/nurture_contacts.json` (gitignored) — live contact state:
    `track`, `enrolled_at`, `completed_steps`, `active`, plus
    `last_inbound_id` cursor for the SimpleTexting inbox poll.
  - `lead-automation/nurture_log.json` (gitignored) — every send attempt with
    status code + response body. This is the source of truth for "did Isaiah
    actually get texted twice?"
  - `lead-automation/lead_monitor.py`, `birthday_campaign.py`, `dashboard/` —
    siblings of the engine.
  - `lead-automation/config.py` reads SimpleTexting creds + Justin's personal
    cell from `.env` / `config.json`.

- **`claude/mac-mini-always-on-NUXt4`** — launchd setup so the Mac mini stays
  up and re-runs `claude` on crash. Installed via
  `scripts/mac-mini-always-on/install.sh`. Two LaunchAgents:
  - `com.juddy.claude-code` — runs the `claude` CLI in repo root, KeepAlive on
    crash, ThrottleInterval=30. Logs to `~/Library/Logs/juddy/claude-code.{out,err}.log`.
  - `com.juddy.healthcheck` — `healthcheck.sh` every 5 min.
  - The nurture daemon itself is **not** wired into launchd here — it's run
    separately (likely a different LaunchAgent or `nohup python3 nurture_engine.py daemon` on the mini).

- **`claude/auto-insurance-comparison-agent-Q9v8T`** — separate insurance
  comparison agent. Unrelated to nurture.

## Voice — message content style

When writing or generating outbound text content, Justin's voice is **short,
direct, conversational**. Default openers:

- ✅ `Hey {name}!` / `Hey {name} —`
- ✅ `Morning!` / `Hey!`

Avoid:

- ❌ `Quick one for you {name}` — too cute / formal
- ❌ `Real quick {name}` — same
- ❌ `Pro tip:` / `Heads up,` / `Fun fact —` / `FYI` openers — stilted
- ❌ `Just wanted to circle back on…` — wordy

Closers like `— Justin` are fine. Emoji at end of line is fine sparingly.
Multi-paragraph nurture texts should still feel like one human texting another,
not a marketing email.

## Conventions

- Phone numbers are normalized via `_digits()` (strip non-digits, drop leading
  US `1`). Always compare phones with `_digits()`, not raw strings.
- `completed_steps` is the dedupe key for "have we already sent step X to this
  contact?" If `enrolled_at` resets but `completed_steps` doesn't (or vice
  versa), steps re-fire.
- `process_contacts` saves contacts immediately after each send, AND
  `sms.send_sms_once` writes the ledger before returning. Both are
  belt-and-suspenders against the duplicate-send foot-gun.
- The repo's GitHub remote is `summitaiautomations-ui/juddy`.

## Common asks

- **"X got the same text twice"** → if it's after the dedupe rollout, that
  shouldn't happen. Check `sms_ledger.json` for the `(phone, text)` key.
  If the key is missing, something is bypassing `send_sms_once` — grep for
  `simpletexting.com` to find the rogue caller.
- **"Add a lead"** → `python3 nurture_engine.py add "Name" +15551234567 hot city=Denver ...`
- **"Pause/resume a contact"** → `deactivate <phone>` / `reactivate <phone> [track]`.
