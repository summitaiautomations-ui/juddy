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
Connects to Gmail via IMAP and walks new UIDs since the last successful
scan. Each email is classified by sender as either a **reply** from an
existing lead, or a **new Realtor.com lead notification**.

**Reply** (existing lead's email matches a Notion record):
1. Appends to the record's Notes:
   `[YYYY-MM-DD HH:MM via Gmail] RCVD: <subject> — <excerpt>`
2. Sets Last Contact to today.
3. Bumps Priority from Cold → Warm (if currently Cold).
4. Sends a single SMS nudge to Justin's personal cell.
5. Queues the reply for the daily digest.

**Realtor.com new lead** (sender domain is `realtor.com`):
1. Parses Name / Phone / Email / Property / Credit / Income / Down /
   Timeline / etc out of the notification body.
2. Dedupe check by phone — if the lead is already in the pipeline,
   appends a "re-received" note and skips the welcome.
3. Creates a new Notion record (Status=Lead, Priority=Hot, Lead Source=
   Realtor.com, Date Added=today, plus a one-block notes summary).
4. Sends the initial welcome SMS via `WELCOME_MESSAGE_TEMPLATE`
   (dedupe namespace = Lead ID, so the same lead can never be
   welcomed twice). **Suppressed until the env var is set** — Notion
   record is still created, no text fires.
5. Appends `[YYYY-MM-DD] AUTO welcome SMS sent` (or `NOT sent`) to Notes.
6. Queues the new lead for the daily digest.

First run captures the current max UID as a baseline and exits without
processing — no back-fill of historical email.

### `day1_info`
A second Day-1 touch sent **a couple of hours after the welcome**, during
business hours only (default 9–17 local). For each lead added today whose
Notes show the welcome marker but not yet an info-touch marker, sends an
SMS with generic info about Justin + Summit Mortgage + linktree link.

Sent **regardless of whether the lead has already replied** — per Justin's
ask, the Day-1 sequence fires both touches no matter what. The
"engagement = stop nurture" rule applies to later flows, not this one.

Idempotent via SMS-ledger namespace `info_touch:<page_id>` plus a Notes
marker check. Outside business hours, exits cleanly without sending.

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
   for job in outreach-birthday outreach-scan outreach-day1-info outreach-digest; do
     plist=scripts/outreach/com.juddy.${job}.plist.template
     dst=~/Library/LaunchAgents/com.juddy.${job}.plist
     sed "s|__REPO__|$HOME/juddy|g; s|__USER__|$USER|g" "$plist" > "$dst"
     launchctl load "$dst"
   done
   ```

   Cadence:
   - `birthday` — daily 10:00
   - `scan` — every 10 minutes
   - `day1_info` — every hour at :15 (gated to business hours in code)
   - `digest` — daily 08:00

## State files (gitignored)
- `outreach/sms_ledger.json` — every successful outbound SMS with
  dedupe metadata. Don't delete; that's how dup-prevention survives
  crashes.
- `outreach/inbound_ledger.json` — last seen Gmail UID + today's
  digest queue. Don't delete mid-day or scan will re-baseline and
  the digest will be empty.
