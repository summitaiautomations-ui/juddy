import crypto from 'node:crypto';
import { config } from './config.js';

/**
 * Quo is the rebrand of OpenPhone, so this maps the OpenPhone v-series webhook
 * schema. Confirm once with a real "test event" from Quo's webhook settings, in
 * case field names shift under the Quo branding.
 *
 * Signature: Quo/OpenPhone sends an `openphone-signature` header shaped like
 *   hmac;1;<timestamp>;<base64-digest>
 * The digest is HMAC-SHA256 over `<timestamp>.<rawBody>` using the base64-decoded
 * signing key shown in Quo's webhook settings.
 */
export function verifyWebhook(req) {
  if (!config.quoSigningKey) return true; // no key configured → skip (dev only)

  const header = req.get('openphone-signature') || req.get('quo-signature');
  if (!header) return false;

  const parts = header.split(';');
  const timestamp = parts[2];
  const providedDigest = parts[3];
  if (!timestamp || !providedDigest) return false;

  const signedData = `${timestamp}.${req.rawBody || ''}`;
  const key = Buffer.from(config.quoSigningKey, 'base64');
  const computed = crypto.createHmac('sha256', key).update(signedData).digest('base64');

  try {
    return crypto.timingSafeEqual(Buffer.from(computed), Buffer.from(providedDigest));
  } catch {
    return false;
  }
}

const asArray = (v) => (Array.isArray(v) ? v : v ? [v] : []);

/**
 * Normalize a Quo webhook into:
 *   { type, direction, timestamp, transcript, summary, candidatePhones, callId }
 *
 * candidatePhones lists every number on the event; the server tries each against
 * Notion and keeps the first that matches a record (so we never need to know
 * which of your own Quo numbers is which).
 */
export function parseEvent(body) {
  const type = body.type || '';
  const obj = body.data?.object || {};
  const timestamp = body.createdAt || obj.createdAt || obj.completedAt || undefined;

  // --- text messages: message.received / message.delivered ---
  if (type.startsWith('message.')) {
    const from = obj.from;
    const to = asArray(obj.to);
    const incoming = obj.direction === 'incoming';
    const who = incoming ? 'Them' : 'Me';
    return {
      type,
      direction: incoming ? 'inbound text' : 'outbound text',
      touchpointType: 'Text',
      timestamp,
      transcript: obj.body ? `${who}: ${obj.body}` : '',
      summary: undefined,
      candidatePhones: [from, ...to].filter(Boolean),
      callId: undefined,
    };
  }

  // --- call transcript: has per-line speaker phone numbers in `dialogue` ---
  if (type === 'call.transcript.completed') {
    const dialogue = asArray(obj.dialogue);
    const phones = [...new Set(dialogue.map((d) => d.identifier).filter(Boolean))];
    const transcript = dialogue
      .map((d) => `${d.identifier || 'Speaker'}: ${d.content || ''}`)
      .join('\n');
    return {
      type,
      direction: 'call',
      touchpointType: 'Phone Call',
      timestamp,
      transcript,
      summary: undefined,
      candidatePhones: phones,
      callId: obj.callId || obj.id,
    };
  }

  // --- call summary: AI notes; no phone in payload, matched via callId cache ---
  if (type === 'call.summary.completed') {
    const summary = asArray(obj.summary).join('\n');
    const nextSteps = asArray(obj.nextSteps);
    const summaryText = [summary, nextSteps.length ? `Next steps:\n- ${nextSteps.join('\n- ')}` : '']
      .filter(Boolean)
      .join('\n\n');
    return {
      type,
      direction: 'call',
      touchpointType: 'Phone Call',
      timestamp,
      transcript: '',
      summary: summaryText,
      candidatePhones: asArray(obj.participants).filter(Boolean),
      callId: obj.callId || obj.id,
    };
  }

  // --- call completed: no notes, but lets us learn callId → phone ---
  if (type === 'call.completed' || type === 'call.recording.completed') {
    return {
      type,
      direction: 'call',
      touchpointType: 'Phone Call',
      timestamp,
      transcript: '',
      summary: undefined,
      candidatePhones: asArray(obj.participants).filter(Boolean),
      callId: obj.id || obj.callId,
    };
  }

  return { type, direction: undefined, timestamp, transcript: '', summary: undefined, candidatePhones: [], callId: undefined };
}
