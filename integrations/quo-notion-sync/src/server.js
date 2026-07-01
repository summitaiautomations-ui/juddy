import express from 'express';
import { config } from './config.js';
import { verifyWebhook, parseEvent } from './quo.js';
import { findRecordByPhone, appendConversation } from './notion.js';

const app = express();

// Capture the raw body so webhook signatures can be verified.
app.use(
  express.json({
    verify: (req, _res, buf) => {
      req.rawBody = buf.toString('utf8');
    },
  })
);

app.get('/health', (_req, res) => res.json({ ok: true }));

app.post('/webhooks/quo', async (req, res) => {
  if (!verifyWebhook(req)) {
    console.warn('[quo] webhook signature verification failed');
    return res.status(401).json({ error: 'invalid signature' });
  }

  let event;
  try {
    event = parseEvent(req.body);
  } catch (err) {
    console.error('[quo] failed to parse event', err);
    return res.status(400).json({ error: 'unparseable payload' });
  }

  if (!event.phone) {
    console.warn('[quo] event had no contact phone; skipping');
    return res.status(202).json({ status: 'skipped', reason: 'no phone' });
  }
  if (!event.transcript && !event.summary) {
    return res.status(202).json({ status: 'skipped', reason: 'no content' });
  }

  try {
    const record = await findRecordByPhone(event.phone);
    if (!record) {
      console.warn(`[quo] no Notion record matched phone ${event.phone}`);
      return res.status(202).json({ status: 'unmatched', phone: event.phone });
    }
    const result = await appendConversation(record, event);
    console.log(`[quo] appended conversation to ${result.dataSource} record ${result.pageId}`);
    return res.json({ status: 'ok', ...result });
  } catch (err) {
    console.error('[quo] failed to write to Notion', err);
    return res.status(500).json({ error: 'notion write failed' });
  }
});

app.listen(config.port, () => {
  console.log(`quo-notion-sync listening on :${config.port}`);
  console.log(`  webhook endpoint: POST /webhooks/quo`);
});
