# Quo → Notion communications sync

Watches your **Quo** (formerly OpenPhone) workspace for calls and text
messages, pulls **call transcripts + AI summaries**, matches the other
party's phone number against your Notion contact databases, and files
everything into the **📞 Communications** database in Notion:

- One row per call (transcript + AI summary in the page body) and one row
  per text message.
- Rows are auto-linked to the matching **Realtor Contact** or **Lead** by
  phone number, and the contact's **Last Contact** date is bumped.
- Transcripts that aren't ready yet are marked *Pending* and back-filled
  automatically on a later run.
- Runs every 5 minutes on the always-on Mac mini via launchd. Stdlib-only
  Python — nothing to install.

## One-time setup

### 1. Get a Quo API key

Quo dashboard → **Settings → Integrations → API** → generate an API key
(workspace owner/admin required).

> Call transcripts and AI summaries via API require Quo's **Business** plan.
> Calls and texts sync on any plan with API access; transcript rows are just
> marked *Unavailable* if the plan doesn't include them.

### 2. Create a Notion integration and share the databases

1. https://www.notion.so/profile/integrations → **New integration**
   (internal), copy the secret (`ntn_…`).
2. In Notion, open each of these and connect the integration
   (••• menu → *Connections* → your integration):
   - **📞 Communications** (the sync writes here)
   - **Realtor Contacts** and **📇 Leads** (the sync reads phone numbers and
     updates Last Contact)

### 3. Configure and install (on the Mac mini)

```bash
bash scripts/quo-notion-sync/install.sh   # first run seeds the config file
vi ~/.config/juddy/quo-notion-sync.json   # paste your two keys
bash scripts/quo-notion-sync/install.sh   # dry-runs, then installs the agent
```

The installer does a `--dry-run` first so you can see what would sync before
anything is written.

## How matching works

Phone numbers are compared on their **last 10 digits**, so `(612) 555-1234`,
`+16125551234`, and `612-555-1234` all match. A call from a number that isn't
in either contact database still gets a Communications row — it just isn't
linked to a contact. Add the number to a contact and future calls/texts link
automatically.

**Leads now has a `Phone` property** (added for this sync) — fill it in for
any lead you call or text from Quo.

## Day-to-day

```bash
# What's it doing?
tail -f ~/Library/Logs/juddy/quo-notion-sync.log

# Force a sync right now
launchctl kickstart -k gui/$(id -u)/com.juddy.quo-notion-sync

# Run by hand with extra detail
python3 scripts/quo-notion-sync/sync.py --verbose

# Preview without writing to Notion
python3 scripts/quo-notion-sync/sync.py --dry-run --verbose

# First-run backfill deeper than the default 72h
python3 scripts/quo-notion-sync/sync.py --backfill-hours 720
```

State lives in `~/.local/state/juddy/quo-notion-sync/state.json` (sync
watermark, processed IDs, pending transcripts). Deleting it re-scans the
backfill window; already-synced items are skipped via the `Quo ID` dedupe
check, so no duplicates.

## Config reference (`~/.config/juddy/quo-notion-sync.json`)

| key | meaning |
| --- | --- |
| `quo_api_key` | Quo API key (sent as `Authorization` header) |
| `notion_token` | Notion internal integration secret |
| `communications_database_id` | Notion DB the rows are created in |
| `contact_databases[]` | DBs to match against: `phone_property` (phone field), `relation_property` (relation on Communications), `last_contact_property` (date to bump, or `null`) |
| `poll_calls` / `poll_messages` | turn either stream off |
| `backfill_hours` | lookback window on first run (default 72) |

## How it works / notes

- Polls `GET /v1/conversations` for activity since the last run, then
  `GET /v1/calls` and `GET /v1/messages` per active conversation, then
  `GET /v1/call-transcripts/{id}` and `GET /v1/call-summaries/{id}`.
  Base URL is `https://api.openphone.com/v1` (still the official host after
  the Quo rebrand).
- Runs are incremental with a 30-minute overlap window; duplicates are
  prevented by the `Quo ID` property lookup before every insert.
- An alternative to polling is Quo **webhooks** (`call.transcript.completed`,
  `message.received`, …), which are push-based but need a public HTTPS
  endpoint — polling every 5 minutes avoids exposing the Mac mini to the
  internet and is plenty fresh for CRM notes.
