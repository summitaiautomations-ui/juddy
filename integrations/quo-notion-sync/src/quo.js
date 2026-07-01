import crypto from 'node:crypto';
import { config } from './config.js';

/**
 * Verify the webhook really came from Quo.
 *
 * TODO (needs Quo docs): confirm how Quo signs webhooks. Two common schemes are
 * supported below — pick the one Quo uses and delete the other:
 *   A) HMAC-SHA256 of the raw body in a header (e.g. X-Quo-Signature).
 *   B) A static shared secret sent in a header.
 * If Quo does neither, restrict access another way (secret in the URL path).
 */
export function verifyWebhook(req) {
  if (!config.quoWebhookSecret) return true; // no secret configured → skip (dev only)

  // Scheme A: HMAC signature over the raw body.
  const sig = req.get('X-Quo-Signature'); // TODO: confirm header name
  if (sig) {
    const expected = crypto
      .createHmac('sha256', config.quoWebhookSecret)
      .update(req.rawBody || '')
      .digest('hex');
    try {
      return crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected));
    } catch {
      return false;
    }
  }

  // Scheme B: static shared secret header.
  const headerSecret = req.get('X-Quo-Secret'); // TODO: confirm header name
  if (headerSecret) return headerSecret === config.quoWebhookSecret;

  return false;
}

/**
 * Map Quo's webhook payload into the shape appendConversation() expects.
 *
 * TODO (needs Quo docs): replace the field paths below with Quo's real payload.
 * The normalized shape we need is:
 *   { phone, direction, timestamp, summary, transcript }
 *   - phone:      the client/recruit's number (NOT your Quo number)
 *   - direction:  "inbound" | "outbound" | "conversation" (optional label)
 *   - timestamp:  ISO string or epoch ms of the message/conversation
 *   - summary:    AI notes / summary of the chat (optional)
 *   - transcript: full text of the conversation/message
 */
export function parseEvent(body) {
  // ---- placeholder mapping — adjust to Quo's actual JSON ----
  const contactPhone =
    body.contact?.phone ??
    body.from ??
    body.customer?.phone_number ??
    null;

  const transcript =
    body.transcript ??
    body.message?.text ??
    (Array.isArray(body.messages)
      ? body.messages
          .map((m) => `${m.direction === 'outbound' ? 'Me' : 'Them'} [${m.timestamp || ''}]: ${m.text || m.body || ''}`)
          .join('\n')
      : '') ??
    '';

  return {
    phone: contactPhone,
    direction: body.direction || (Array.isArray(body.messages) ? 'conversation' : undefined),
    timestamp: body.timestamp || body.created_at || body.ended_at || undefined,
    summary: body.summary || body.ai_notes || undefined,
    transcript,
  };
}
