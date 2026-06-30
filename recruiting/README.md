# recruiting

Daily recruiting digest — one snazzy HTML email each morning tracking
progress toward the hiring goal (default **12 hires, each producing 2–3
units/month** last year), sourced live from the Notion **Recruiting
Pipeline** database.

Each email shows:

- **Goal progress** — `X / 12 hired`, a progress bar, and how many to go
- **Production caliber** — how many hires hit the 2–3 u/mo target, the
  hired average u/mo, and the monthly book of business added (2025 Units
  is annual, so u/mo = units ÷ 12)
- **Stat strip** — active candidates, in-Offer, in-Interview, new this week
- **Overdue alert** — late-stage follow-ups that have gone past due
- **On the doorstep** — every Offer / Interview candidate (the next hires
  most likely come from here), with role, location, production, and
  recruiter
- **Funnel** — Initial Outreach → Conversation → Interview → Offer → Hired
- **Hired so far** — a roll call of everyone already across the line

## Setup (Mac mini)

1. Install deps (shares the repo-root `.env` with `outreach/`):
   ```bash
   cd ~/juddy
   python3 -m venv recruiting/.venv
   recruiting/.venv/bin/pip install -r recruiting/requirements.txt
   ```

2. Add the keys from `recruiting/.env.example` to `~/juddy/.env`. If
   `outreach/` is already running, only two are new: `NOTION_RECRUITING_DB`
   (optional) and `RECRUITING_DIGEST_TO`.

## Usage

```bash
# Send today's digest
recruiting/.venv/bin/python -m recruiting daily

# Print the plain-text version without sending
recruiting/.venv/bin/python -m recruiting daily --dry-run

# Render the HTML to recruiting/preview.html (open it in a browser)
recruiting/.venv/bin/python -m recruiting preview
```

## Schedule it (launchd)

Run `daily` once each morning, e.g. 7:00 AM, with a `launchd` agent — the
same pattern as the other always-on jobs in
`scripts/mac-mini-always-on/`.

## Configuration

| Env var | Default | Meaning |
| --- | --- | --- |
| `HIRING_GOAL` | `12` | The number of hires the email tracks toward |
| `TARGET_UPM_MIN` | `2` | Lower bound of the units/mo caliber target |
| `TARGET_UPM_HIGH` | `3` | Upper bound, for the "2–3 u/mo" label |
| `NOTION_RECRUITING_DB` | known DB id | Recruiting Pipeline database |
| `RECRUITING_DIGEST_TO` | `DIGEST_TO_EMAIL` | Recipient(s), comma-separated |
| `RECRUITING_OVERDUE_DAYS` | `0` | Grace days before a follow-up is "overdue" |
