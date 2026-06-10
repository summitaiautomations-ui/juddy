# outreach

Mortgage-pipeline outreach (SMS + Notion sync). Replaces the legacy
`lead-automation/` project after its templating bugs sent wrong-name texts.

Single source of truth is the Notion Mortgage Pipeline database — no
local contacts file to keep in sync.

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

On every successful send a line is appended to the client's Notes:
```
[YYYY-MM-DD] 🎂 Birthday freebie text sent (7 days out from DOB).
```

## Setup (Mac mini)

1. Create the venv and install deps:
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

3. Dry run today's birthday window without scheduling:
   ```bash
   outreach/.venv/bin/python -m outreach birthday
   ```
   Output ends with a single summary line:
   `birthday YYYY-MM-DD: sent=N already_noted=N sms_dedupe=N failed=N`

4. Install the daily launchd job (runs at 10:00 local):
   ```bash
   # one-time, after you've reviewed the plist template
   cp scripts/outreach/com.juddy.outreach-birthday.plist.template /tmp/p.plist
   sed -i '' "s|__REPO__|$HOME/juddy|g; s|__USER__|$USER|g" /tmp/p.plist
   cp /tmp/p.plist ~/Library/LaunchAgents/com.juddy.outreach-birthday.plist
   launchctl load ~/Library/LaunchAgents/com.juddy.outreach-birthday.plist
   ```

## State files (gitignored)
- `outreach/sms_ledger.json` — every successful SMS with dedupe metadata.
  Don't delete; that's how dup-prevention survives crashes.
