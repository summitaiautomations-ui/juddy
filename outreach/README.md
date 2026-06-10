# outreach

Mortgage-pipeline outreach (SMS + Notion sync). Replaces the legacy
`lead-automation/` project after its templating bugs sent wrong-name texts.

Single source of truth is the Notion Mortgage Pipeline database — no
local contacts file to keep in sync.

## Design

- **Outbound (SMS to leads)** → Simply Texting API. Birthday + future
  initial outreach + a couple of nurture touches. Stops on engagement.
- **Inbound (replies from leads)** → Gmail IMAP. Every 10 min scan,
  matched to the Notion record by sender email.
- **Engagement = stop nurture.** As soon as a lead has any `RCVD:` line
  in their Notion Notes, future nurture flows skip them — Justin is
  taking over the conversation manually.
- **Notification to Justin** → a single short SMS to his personal cell
  the moment a lead reply lands. Dedupe scoped to one nudge per lead
  per day. No misfiring "Hey {client}" pattern — just `"{name} replied
  — your turn."` (override via `NUDGE_MESSAGE_TEMPLATE`).
- **Daily digest** → one plain-text email at 08:00 summarizing new
  replies in the last 24h plus all overdue follow-ups. No per-event
  email noise.

## Flows

### `birthday`
Texts every past client (`Status` ∈ Funded / Friends and Family) a
"happy early birthday" message **7 days before their birthday**.

Idempotent per year via two layers:
1. `sms.py`'s normalized-text + sentence-overlap dedupe ledger
   (`outreach/sms_ledger.json`), scoped to namespace `birthday:YYYY`.
2. A Notes check: if the client already has a `🎂 Birthday freebie text
   sent` line stamped with this year, skip them — protects against a
   ledger reset double-firing.

On every successful send, a line is appended to the client's Notes:
```
[YYYY-MM-DD] 🎂 Birthday freebie text sent (7 days out from DOB).
```

### `scan`
Connects to Gmail via IMAP, walks new UIDs since the last successful
scan, parses From/Subject/body, and matches against active Notion
records by email address.

For each matched reply:
1. Appends to the record's Notes:
   `[YYYY-MM-DD HH:MM via Gmail] RCVD: <subject> — <excerpt>`
2. Sets Last Contact to today.
3. Bumps Priority from Cold → Warm (if currently Cold).
4. Sends a single SMS nudge to Justin's personal cell.
5. Queues the reply for the daily digest.

First run captures the current max UID as a baseline and exits without
processing — no back-fill of historical email.

### `digest`
One email at 08:00 each day. Pulls replies from `inbound_ledger.json`
(populated by `scan`) and overdue follow-ups from Notion. Sends via
Gmail SMTP, then clears the reply queue.

## Setup (Mac mini)

1. Install deps:
   ```bash
   cd ~/juddy
   python3 -m venv outreach/.venv
   outreach/.venv/bin/pip install -r outreach/requirements.txt
   ```

2. Create `~/juddy/.env` from `outreach/.env.example`. Fill in:
   - Simply Texting API key + account phone
   - Notion integration token (created at
     https://www.notion.so/profile/integrations, then shared with the
     Mortgage Pipeline database from inside Notion)
   - Gmail address + app password (generate at
     https://myaccount.google.com/apppasswords; 2-Step Verification
     must be on)
   - `DIGEST_TO_EMAIL` (where the daily digest lands)
   - `JUSTIN_PERSONAL_CELL` (where reply nudges land, 10-digit US)

3. Smoke test each flow without scheduling:
   ```bash
   outreach/.venv/bin/python -m outreach birthday   # dry-run today's window
   outreach/.venv/bin/python -m outreach scan       # baseline-set the inbox UID on first run
   outreach/.venv/bin/python -m outreach digest     # send today's digest now
   ```

4. Install the launchd jobs:
   ```bash
   for job in outreach-birthday outreach-scan outreach-digest; do
     plist=scripts/outreach/com.juddy.${job}.plist.template
     dst=~/Library/LaunchAgents/com.juddy.${job}.plist
     sed "s|__REPO__|$HOME/juddy|g; s|__USER__|$USER|g" "$plist" > "$dst"
     launchctl load "$dst"
   done
   ```

   Cadence:
   - `birthday` — daily 10:00
   - `scan` — every 10 minutes
   - `digest` — daily 08:00

## State files (gitignored)
- `outreach/sms_ledger.json` — every successful outbound SMS with
  dedupe metadata. Don't delete; that's how dup-prevention survives
  crashes.
- `outreach/inbound_ledger.json` — last seen Gmail UID + today's
  digest queue. Don't delete mid-day or scan will re-baseline and
  the digest will be empty.
