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

## Two emails

- **`daily`** — the goal-tracking digest: progress toward the hiring goal
  and the 2–3 u/mo production caliber, on-the-doorstep candidates, overdue
  follow-ups, funnel, and hired roll call.
- **`weekly`** — a funnel-health review with **no goal/caliber numbers**:
  Top / Middle / Bottom of funnel counts with week-over-week movement (who
  advanced a stage, new entries, hired/passed this week). It saves a
  snapshot (`recruiting/.weekly_state.json`, gitignored) each run and diffs
  against last week's; the first run just establishes the baseline.

  Funnel buckets: Top = Initial Outreach · Middle = Conversation, Interview
  · Bottom = Offer. Hired/Passed are exits, reported as "this week," not
  standing buckets.

## Usage

```bash
# Daily digest
recruiting/.venv/bin/python -m recruiting daily
recruiting/.venv/bin/python -m recruiting daily --dry-run

# Weekly funnel review (--dry-run does not send or save a snapshot)
recruiting/.venv/bin/python -m recruiting weekly
recruiting/.venv/bin/python -m recruiting weekly --dry-run

# Render either to recruiting/preview.html (open in a browser)
recruiting/.venv/bin/python -m recruiting preview
recruiting/.venv/bin/python -m recruiting preview weekly
```

## Schedule it (launchd)

One installer wires up both agents — daily every morning (7:00 AM) and
weekly on Monday (7:30 AM):

```bash
bash recruiting/install-schedule.sh
```

Override times with env vars, e.g. `DIGEST_HOUR=6 DIGEST_MINUTE=30` for the
daily, or `WEEKLY_WEEKDAY=1 WEEKLY_HOUR=8` for the weekly (Weekday: 0/7=Sun,
1=Mon). Matches the always-on pattern in `scripts/mac-mini-always-on/`.

## Configuration

| Env var | Default | Meaning |
| --- | --- | --- |
| `HIRING_GOAL` | `12` | The number of hires the email tracks toward |
| `TARGET_UPM_MIN` | `2` | Lower bound of the units/mo caliber target |
| `TARGET_UPM_HIGH` | `3` | Upper bound, for the "2–3 u/mo" label |
| `NOTION_RECRUITING_DB` | known DB id | Recruiting Pipeline database |
| `RECRUITING_DIGEST_TO` | `DIGEST_TO_EMAIL` | Recipient(s), comma-separated |
| `RECRUITING_OVERDUE_DAYS` | `0` | Grace days before a follow-up is "overdue" |
