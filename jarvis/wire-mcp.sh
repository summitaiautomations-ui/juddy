#!/usr/bin/env bash
# Wire the `claude` CLI on this Mac mini to the MCP servers Jarvis's brain needs
# (Notion for the pipelines, Gmail for email). Registers them at USER scope so
# every project — including Jarvis's workspace — can use them.
#
#   bash jarvis/wire-mcp.sh
#
# Notion uses its hosted endpoint (OAuth happens later via `claude` -> /mcp).
# Gmail has no single standard endpoint, so provide yours via env vars:
#   GMAIL_MCP_URL=https://...                 (required to wire Gmail)
#   GMAIL_MCP_TRANSPORT=http|sse              (default: http)
#   GMAIL_MCP_HEADER="Authorization: Bearer …"  (optional, repeatable via GMAIL_MCP_HEADER2)
set -euo pipefail

CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || true)}"
if [[ -z "${CLAUDE_BIN}" ]]; then
  echo "error: claude CLI not found on PATH (set CLAUDE_BIN=/path/to/claude)" >&2
  exit 1
fi

NOTION_URL="${NOTION_MCP_URL:-https://mcp.notion.com/mcp}"

echo "==> Registering Notion (HTTP, user scope): ${NOTION_URL}"
if "${CLAUDE_BIN}" mcp get notion >/dev/null 2>&1; then
  echo "    notion already configured — skipping"
else
  "${CLAUDE_BIN}" mcp add --transport http --scope user notion "${NOTION_URL}"
fi

if [[ -n "${GMAIL_MCP_URL:-}" ]]; then
  transport="${GMAIL_MCP_TRANSPORT:-http}"
  echo "==> Registering Gmail (${transport}, user scope): ${GMAIL_MCP_URL}"
  args=(mcp add --transport "${transport}" --scope user gmail "${GMAIL_MCP_URL}")
  [[ -n "${GMAIL_MCP_HEADER:-}" ]]  && args+=(--header "${GMAIL_MCP_HEADER}")
  [[ -n "${GMAIL_MCP_HEADER2:-}" ]] && args+=(--header "${GMAIL_MCP_HEADER2}")
  if "${CLAUDE_BIN}" mcp get gmail >/dev/null 2>&1; then
    echo "    gmail already configured — skipping"
  else
    "${CLAUDE_BIN}" "${args[@]}"
  fi
else
  echo "==> Gmail: set GMAIL_MCP_URL to wire it (skipped)"
fi

echo
echo "Configured MCP servers:"
"${CLAUDE_BIN}" mcp list || true

cat <<'EOF'

Next: run `claude` once and type `/mcp` to complete the OAuth/login flow for
any server that needs it (Notion will open a browser). After that, Jarvis's
brain can read and update your pipelines and search email on its own.
EOF
