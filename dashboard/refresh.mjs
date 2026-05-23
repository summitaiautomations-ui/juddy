#!/usr/bin/env node
// Re-pulls the Recruiting Pipeline from Notion and regenerates the dashboard
// data files (data.json + data.js). Run on a schedule (see the launchd
// template in scripts/mac-mini-always-on/) to keep the dashboard fresh.
//
// Setup (one time):
//   1. Create a Notion internal integration: https://www.notion.so/my-integrations
//   2. Share the "Recruiting Pipeline" database with that integration.
//   3. Export the token before running:  export NOTION_TOKEN=ntn_xxx
//
// Usage:  NOTION_TOKEN=ntn_xxx node refresh.mjs

import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const TOKEN = process.env.NOTION_TOKEN;
const DATABASE_ID =
  process.env.NOTION_DATABASE_ID || "e0a85bb7a0514af1b54992580e4bddb5";
const NOTION_VERSION = "2022-06-28";

if (!TOKEN) {
  console.error("ERROR: NOTION_TOKEN env var is required.");
  process.exit(1);
}

const here = dirname(fileURLToPath(import.meta.url));

// Map a Notion property object to a plain JS value.
function readProp(p) {
  if (!p) return null;
  switch (p.type) {
    case "title":
    case "rich_text":
      return (p[p.type] || []).map((t) => t.plain_text).join("") || "";
    case "number":
      return p.number;
    case "select":
      return p.select ? p.select.name : null;
    case "multi_select":
      return (p.multi_select || []).map((s) => s.name).join(", ");
    case "date":
      return p.date ? p.date.start : null;
    case "phone_number":
      return p.phone_number;
    case "email":
      return p.email;
    case "url":
      return p.url;
    default:
      return null;
  }
}

const FIELDS = {
  name: "Candidate Name",
  stage: "Stage",
  priority: "Priority",
  role: "Role Type",
  company: "Current Company",
  city: "City",
  state: "State",
  units: "2025 Units",
  volume: "2025 Volume",
  recruiter: "Assigned Recruiter",
  source: "Source",
  nurture: "Nurture Stage",
  lastTouch: "Last Touchpoint Type",
  nmls: "NMLS #",
  phone: "Phone",
  email: "Email",
  dateAdded: "Date Added",
  lastContact: "Last Contact",
  nextFollowUp: "Next Follow-Up",
  notes: "Notes",
  engagement: "Engagement Notes",
};

async function queryAll() {
  const records = [];
  let cursor;
  do {
    const res = await fetch(
      `https://api.notion.com/v1/databases/${DATABASE_ID}/query`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${TOKEN}`,
          "Notion-Version": NOTION_VERSION,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(cursor ? { start_cursor: cursor, page_size: 100 } : { page_size: 100 }),
      },
    );
    if (!res.ok) {
      throw new Error(`Notion API ${res.status}: ${await res.text()}`);
    }
    const json = await res.json();
    for (const page of json.results) {
      const rec = { url: page.url };
      for (const [key, prop] of Object.entries(FIELDS)) {
        rec[key] = readProp(page.properties[prop]);
      }
      if (rec.name && rec.name.trim()) records.push(rec);
    }
    cursor = json.has_more ? json.next_cursor : null;
  } while (cursor);
  return records;
}

const now = new Date();
const generatedAt = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;

const records = await queryAll();
const payload = { generatedAt, records };

writeFileSync(join(here, "data.json"), JSON.stringify(payload, null, 2));
writeFileSync(
  join(here, "data.js"),
  `window.PIPELINE_PAYLOAD = ${JSON.stringify(payload, null, 2)};\n`,
);

console.log(`[${new Date().toISOString()}] Refreshed ${records.length} candidates (snapshot ${generatedAt}).`);
