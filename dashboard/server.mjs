#!/usr/bin/env node
// Serves the recruiting dashboard AND writes drag-and-drop stage changes
// back to Notion. Replaces the plain static file server when you want
// two-way sync.
//
// Setup:  export NOTION_TOKEN=ntn_xxx   (integration must have edit access)
// Run:    node server.mjs               (then open http://localhost:8800)

import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const DIR = dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.DASHBOARD_PORT || 8800);
const TOKEN = process.env.NOTION_TOKEN || "";
const NOTION_VERSION = "2022-06-28";

// Stage -> priority convention applied automatically on a move.
const STAGE_PRIORITY = { Offer: "Hot", Interview: "Warm" };

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".css": "text/css; charset=utf-8",
};

function send(res, code, body, type = "text/plain") {
  res.writeHead(code, { "Content-Type": type, "Cache-Control": "no-store" });
  res.end(body);
}

async function notionPatch(pageId, props, token) {
  const res = await fetch(`https://api.notion.com/v1/pages/${pageId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Notion-Version": NOTION_VERSION,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ properties: props }),
  });
  if (!res.ok) throw new Error(`Notion ${res.status}: ${await res.text()}`);
  return res.json();
}

const server = createServer(async (req, res) => {
  // --- API: move a candidate to a new stage ---
  if (req.method === "POST" && req.url === "/api/move") {
    const headerToken = req.headers["x-notion-token"];
    const effective = (typeof headerToken === "string" && headerToken) || TOKEN;
    if (!effective) return send(res, 401, JSON.stringify({ error: "no_token" }), MIME[".json"]);
    let raw = "";
    req.on("data", (c) => (raw += c));
    req.on("end", async () => {
      try {
        const { id, stage } = JSON.parse(raw || "{}");
        if (!id || !stage) return send(res, 400, JSON.stringify({ error: "id and stage required" }), MIME[".json"]);
        const props = { Stage: { select: { name: stage } } };
        if (stage === "Passed") {
          props.Priority = { select: null };
        } else {
          const priority = STAGE_PRIORITY[stage];
          if (priority) props.Priority = { select: { name: priority } };
        }
        await notionPatch(id, props, effective);
        const appliedPriority = stage === "Passed" ? null : (STAGE_PRIORITY[stage] || null);
        send(res, 200, JSON.stringify({ ok: true, stage, priority: appliedPriority }), MIME[".json"]);
      } catch (e) {
        send(res, 502, JSON.stringify({ error: String(e.message || e) }), MIME[".json"]);
      }
    });
    return;
  }

  // --- Static files ---
  let path = decodeURIComponent((req.url || "/").split("?")[0]);
  if (path === "/") path = "/index.html";
  const safe = normalize(join(DIR, path));
  if (!safe.startsWith(DIR)) return send(res, 403, "forbidden");
  try {
    const data = await readFile(safe);
    send(res, 200, data, MIME[extname(safe)] || "application/octet-stream");
  } catch {
    send(res, 404, "not found");
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`Dashboard live at http://localhost:${PORT}`);
  console.log(TOKEN ? "Notion sync: ENABLED" : "Notion sync: DISABLED (set NOTION_TOKEN to enable drag-to-Notion)");
});
