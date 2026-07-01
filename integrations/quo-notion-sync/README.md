# Quo → Notion sync

Auto-appends **Quo conversation transcripts + notes** onto the matching person's
record in Notion, and stamps their **Last Contact** / channel. Built for Summit's
**Recruiting Pipeline** and **Mortgage Pipeline**.

Flow: you text or call a client/recruit in Quo → Quo fires a webhook → this
service finds the Notion record by **phone number** → appends the transcript +
notes and updates contact metadata.

```
Quo text / call ──webhook──▶  quo-notion-sync  ──▶  Notion record
                               (match by phone)      (transcript + Last Contact)
```

> **Quo is the rebrand of OpenPhone**, so this uses the OpenPhone webhook API
> (events like `message.received`, `message.delivered`, `call.transcript.completed`,
> `call.summary.completed`, signed with an `openphone-signature` header).

---

## What it captures

| Quo event | What lands in Notion |
| --- | --- |
| `message.received` / `message.delivered` | The text, labeled Them/Me, + Last Touchpoint = **Text** |
| `call.transcript.completed` | Full call transcript + Last Touchpoint = **Phone Call** |
| `call.summary.completed` | The AI call summary + next steps (attached via the call's ID) |

Every event stamps **Last Contact** and (Mortgage) adds **Quo** to Communication
Channel.

## Setup

1. **Notion integration token** — create at <https://www.notion.so/my-integrations>,
   then open each database (Recruiting Pipeline, Mortgage Pipeline) → `•••` →
   **Connections** → add your integration.
2. **Deploy this service** to any always-on Node host (Render, Railway, Fly.io, a
   small VPS). This repo's container is ephemeral and can't host it.
   ```bash
   cd integrations/quo-notion-sync
   cp .env.example .env      # fill NOTION_TOKEN, then QUO_SIGNING_KEY after step 3
   npm install
   npm start                 # serves POST /webhooks/quo on $PORT
   ```
3. **Create the Quo webhook** — in Quo: **Settings → Webhooks → Create webhook**.
   - URL: `https://<your-host>/webhooks/quo`
   - Events: message received/delivered, call transcript completed, call summary completed
   - Copy the **signing key** Quo shows into `QUO_SIGNING_KEY` in `.env`, then restart.

Sanity-check Notion access + phone matching first:
```bash
node src/find-record.js "+1 612-352-7343"
# → Matched mortgage record: <page-id> ...
```

## One thing to confirm

The field mapping follows OpenPhone's documented schema. Once the webhook is live,
**send one test event from Quo** (or do a real test text) and check it lands on
the right Notion record. If a field is off under the Quo branding, the only file
to adjust is `src/quo.js` (`parseEvent`) — paste me a real event and I'll finalize it.

## How matching works

Notion stores phones in mixed formats (`(612) 352-7343`); Quo sends `+16123527343`.
Both reduce to the **last 10 digits** and compare (`src/phone.js`). The service
tries every phone on the event, so it doesn't need to know which number is yours.
Call summaries carry no phone, so they attach via the call's ID, cached from that
call's transcript/complete event.

## What gets written

A `📱 Quo conversation — <date>` heading + **Notes** + **Transcript** appended to
the person's page; **Last Contact** = today; Recruiting **Last Touchpoint Type**
= Text/Phone Call; Mortgage adds **Quo** to **Communication Channel**.

## Scope

One-way only (Quo → Notion) — no Notion → Quo sending, so there's no sync-loop
risk. Ask if you want outbound later.
