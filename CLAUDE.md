# juddy

Justin's lead-automation + always-on Mac mini stack. The repo has no `main`
branch yet — work is split across feature branches that have not been merged.

## Where things live (by branch)

- **`claude/lead-nurture-workflow-LIHB9`** — Python lead-nurture / SMS engine.
  - `lead-automation/nurture_engine.py` — daemon. Loops every 60s, calls
    `check_inbound_deactivation`, `process_contacts`, periodic
    `check_demotions`. Sends SMS via SimpleTexting
    (`https://api-app2.simpletexting.com/v2/api/messages`).
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

## Conventions

- Phone numbers are normalized via `_digits()` (strip non-digits, drop leading
  US `1`). Always compare phones with `_digits()`, not raw strings.
- `completed_steps` is the dedupe key for "have we already sent step X to this
  contact?" If `enrolled_at` resets but `completed_steps` doesn't (or vice
  versa), steps re-fire.
- `process_contacts` only saves contacts at the END of the per-tick loop
  (after iterating every contact), but it sends SMS immediately. Any
  exception between the send and the final `save_contacts` causes the same
  step to re-fire on the next tick — a known foot-gun for duplicate sends.
- The repo's GitHub remote is `summitaiautomations-ui/juddy`.

## Common asks

- **"X got the same text twice"** → check `nurture_log.json` on the mini for
  duplicate `(contact_phone, step)` rows. Then check whether two daemon
  instances are running (`ps aux | grep nurture_engine`) — that's the most
  common root cause, followed by the save-after-send race in
  `process_contacts`.
- **"Add a lead"** → `python3 nurture_engine.py add "Name" +15551234567 hot city=Denver ...`
- **"Pause/resume a contact"** → `deactivate <phone>` / `reactivate <phone> [track]`.
