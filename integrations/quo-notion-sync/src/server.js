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

// callId → record, so a call.summary.completed (which carries no phone) can
// attach to the same person we matched from the call's transcript/completed event.
const callIndex = new Map(); // callId -> { record, at }
const CALL_TTL_MS = 24 * 60 * 60 * 1000;

function rememberCall(callId, record) {
  if (!callId || !record) return;
  callIndex.set(callId, { record, at: Date.now() });
}
function recallCall(callId) {
  const hit = callId && callIndex.get(callId);
  if (!hit) return null;
  if (Date.now() - hit.at > CALL_TTL_MS) {
    callIndex.delete(callId);
    return null;
  }
  return hit.record;
}

async function matchRecord(event) {
  for (const phone of event.candidatePhones) {
    const record = await findRecordByPhone(phone);
    if (record) return record;
  }
  return recallCall(event.callId);
}

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

  try {
    const record = await matchRecord(event);
    if (!record) {
      console.warn(`[quo] no Notion record matched event ${event.type} (phones: ${event.candidatePhones.join(', ') || 'none'})`);
      return res.status(202).json({ status: 'unmatched', type: event.type });
    }

    // Cache the call→record link so a later summary for this call still lands.
    rememberCall(event.callId, record);

    if (!event.transcript && !event.summary) {
      // e.g. call.completed — we only needed it to learn the callId→record link.
      return res.status(202).json({ status: 'noted', type: event.type });
    }

    const result = await appendConversation(record, event);
    console.log(`[quo] ${event.type} → ${result.dataSource} record ${result.pageId}`);
    return res.json({ status: 'ok', type: event.type, ...result });
  } catch (err) {
    console.error('[quo] failed to write to Notion', err);
    return res.status(500).json({ error: 'notion write failed' });
  }
});

app.listen(config.port, () => {
  console.log(`quo-notion-sync listening on :${config.port}`);
  console.log('  webhook endpoint: POST /webhooks/quo');
});
