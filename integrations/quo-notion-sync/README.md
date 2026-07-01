# Quo → Notion sync

Auto-appends **Quo conversation transcripts + notes** onto the matching person's
record in Notion, and stamps their **Last Contact** / channel. Built for Summit's
**Recruiting Pipeline** and **Mortgage Pipeline**.

Flow: you chat/text a client or recruit in Quo → Quo fires a webhook → this
service finds the Notion record by **phone number** → appends the transcript +
notes to the page and updates contact metadata.

```
Quo conversation ──webhook──▶  quo-notion-sync  ──▶  Notion record
                                (match by phone)      (transcript + Last Contact)
```

---

## Before you build: is a no-code path available?

You connected Claude inside the Quo app. **If Quo lets you add a _Notion
connection_** (look under Connections / Integrations / Apps in Quo), you may be
able to have Quo write transcripts to Notion directly — no server needed. Check
that first. If Quo can't reach Notion on its own, use this service.

---

## What you need

1. **Notion integration token** — create at <https://www.notion.so/my-integrations>,
   then open each database (Recruiting Pipeline, Mortgage Pipeline) → `•••` →
   **Connections** → add your integration so it can read/write.
2. **Quo webhook** — in Quo, point a "new message / conversation completed"
   webhook at `https://<your-host>/webhooks/quo` with a shared secret.
   *(Fill in the exact Quo payload + signature scheme — see TODOs in `src/quo.js`.)*
3. **A host** — any always-on Node host (Render, Railway, Fly.io, a small VPS, or
   a serverless function). This repo's container is ephemeral and can't host it.

## Setup

```bash
cd integrations/quo-notion-sync
cp .env.example .env      # fill in NOTION_TOKEN and QUO_WEBHOOK_SECRET
npm install
npm start                 # starts the webhook server on $PORT (default 8080)
```

Sanity-check Notion access + phone matching before wiring Quo:

```bash
node src/find-record.js "+1 612-352-7343"
# → Matched mortgage record: <page-id> ...
```

## Finishing the Quo side (needs Quo's API docs)

Two spots in `src/quo.js` are marked `TODO` because they depend on Quo's exact
payload:

- **`verifyWebhook`** — confirm how Quo signs webhooks (HMAC header vs. shared
  secret header) and keep the matching branch.
- **`parseEvent`** — map Quo's JSON fields to `{ phone, direction, timestamp,
  summary, transcript }`. The contact **phone** must be the client/recruit's
  number, not your Quo number.

Paste a sample Quo webhook payload and I'll finish these exactly.

## How matching works

Notion stores phones in mixed formats (`(612) 352-7343`); Quo may send
`+16123527343`. Both are reduced to the **last 10 digits** and compared
(`src/phone.js`). The phone→record index is cached for
`PHONE_CACHE_TTL_SECONDS` and rebuilt on a miss so new records are picked up.

## What gets written

- A `📱 Quo conversation — <date>` heading + **Notes** + **Transcript** appended
  to the person's Notion page.
- **Last Contact** set to today.
- Recruiting: **Last Touchpoint Type = Text**. Mortgage: **Quo** added to
  **Communication Channel**.

## Not included (by design)

One-way only (Quo → Notion). No Notion → Quo sending, so there's no risk of a
sync loop. Say the word if you want outbound later.
