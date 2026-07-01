import { Client } from '@notionhq/client';
import { config } from './config.js';
import { matchKey } from './phone.js';

const notion = new Client({ auth: config.notionToken });

// ---- phone → record index (cached) -----------------------------------------
// Notion can't filter reliably on differently-formatted phone strings, so we
// scan each data source once and match in code, caching the result briefly.

let cache = { builtAt: 0, byPhone: new Map() };

async function scanDataSource(ds) {
  const results = [];
  let cursor;
  do {
    const resp = await notion.databases.query({
      database_id: ds.id,
      start_cursor: cursor,
      page_size: 100,
      filter: { property: ds.phoneProp, phone_number: { is_not_empty: true } },
    });
    for (const page of resp.results) {
      const phone = page.properties?.[ds.phoneProp]?.phone_number;
      if (phone) results.push({ pageId: page.id, phone, ds });
    }
    cursor = resp.has_more ? resp.next_cursor : undefined;
  } while (cursor);
  return results;
}

async function buildIndex() {
  const byPhone = new Map();
  for (const ds of config.dataSources) {
    const rows = await scanDataSource(ds);
    for (const row of rows) {
      const key = matchKey(row.phone, config.defaultCountryCode);
      if (key.length === 10 && !byPhone.has(key)) byPhone.set(key, row);
    }
  }
  cache = { builtAt: Date.now(), byPhone };
  return cache;
}

export async function findRecordByPhone(phone) {
  const key = matchKey(phone, config.defaultCountryCode);
  if (key.length !== 10) return null;

  const fresh = Date.now() - cache.builtAt < config.phoneCacheTtlSeconds * 1000;
  if (!fresh || cache.byPhone.size === 0) await buildIndex();

  let hit = cache.byPhone.get(key);
  if (!hit) {
    // Miss might be a brand-new record added after the last scan — rebuild once.
    await buildIndex();
    hit = cache.byPhone.get(key);
  }
  return hit || null;
}

// ---- writing the conversation into the record ------------------------------

function chunk(text, size = 1800) {
  const out = [];
  for (let i = 0; i < text.length; i += size) out.push(text.slice(i, i + size));
  return out;
}

function paragraph(text) {
  return {
    object: 'block',
    type: 'paragraph',
    paragraph: { rich_text: [{ type: 'text', text: { content: text } }] },
  };
}

/**
 * Append a Quo conversation to a Notion page and stamp contact metadata.
 * event = { phone, direction, timestamp, summary, transcript }
 */
export async function appendConversation(record, event) {
  const { ds, pageId } = record;
  const when = event.timestamp ? new Date(event.timestamp) : new Date();
  const whenIso = when.toISOString();
  const dateOnly = whenIso.slice(0, 10);

  // 1) Append transcript + notes to the page body.
  const heading = {
    object: 'block',
    type: 'heading_3',
    heading_3: {
      rich_text: [
        {
          type: 'text',
          text: { content: `📱 Quo conversation — ${dateOnly}${event.direction ? ` (${event.direction})` : ''}` },
        },
      ],
    },
  };

  const blocks = [heading];
  if (event.summary) {
    blocks.push(paragraph(`Notes: ${event.summary}`));
  }
  if (event.transcript) {
    blocks.push(paragraph('Transcript:'));
    for (const part of chunk(event.transcript)) blocks.push(paragraph(part));
  }

  // Notion caps children.append at 100 blocks per call.
  for (let i = 0; i < blocks.length; i += 100) {
    await notion.blocks.children.append({
      block_id: pageId,
      children: blocks.slice(i, i + 100),
    });
  }

  // 2) Update contact metadata (best-effort per property that exists).
  const properties = {};
  if (ds.lastContactProp) {
    properties[ds.lastContactProp] = { date: { start: dateOnly } };
  }
  if (ds.touchpointProp) {
    properties[ds.touchpointProp] = { select: { name: 'Text' } };
  }
  if (ds.channelProp) {
    // Preserve existing channels; add "Quo" if missing.
    const page = await notion.pages.retrieve({ page_id: pageId });
    const existing = page.properties?.[ds.channelProp]?.multi_select?.map((o) => o.name) || [];
    const names = Array.from(new Set([...existing, 'Quo']));
    properties[ds.channelProp] = { multi_select: names.map((name) => ({ name })) };
  }

  if (Object.keys(properties).length) {
    await notion.pages.update({ page_id: pageId, properties });
  }

  return { pageId, dataSource: ds.key };
}
