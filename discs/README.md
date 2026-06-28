# discs

Disc-golf disc inventory + listing generator. v1 ships the listing generator
only — interactive CLI, takes disc details, returns eBay + BST listings via
Claude.

Notion DB + eBay API integration come later (see project plan).

## Setup (Mac mini)

1. Install deps:
   ```bash
   cd ~/juddy
   python3 -m venv discs/.venv
   discs/.venv/bin/pip install -r discs/requirements.txt
   ```

2. Add `ANTHROPIC_API_KEY` to your existing `~/juddy/.env` (the same file
   `outreach/` uses — do **not** create a separate `discs/.env`):
   ```
   ANTHROPIC_API_KEY=sk-ant-api03-...
   ```
   Get a key at https://console.anthropic.com/settings/keys

## Usage

```bash
discs/.venv/bin/python -m discs generate
```

Interactive prompts:
```
Brand: Innova
Mold: Destroyer
Plastic: Star
Weight (g): 175
Color: Red
Sleeve condition (1-10): 8
Special run (optional): 2023 Tour Series
Notes (optional): light rim wear, stamp intact
```

Output is four labeled blocks:
- **eBay TITLE** (with character count vs. the 80-char limit)
- **eBay DESCRIPTION** (plain text, no HTML)
- **BST POST** (markdown for Reddit r/discexchange, DGCR BST forum, or the
  Marketplace Disc Golf app)
- **eBay CATEGORY** breadcrumb
- **COMP PRICING SEARCH** — paste straight into eBay → Advanced → Sold listings

Copy/paste from here into the platform.

## Costs

Uses Claude Opus 4.8 with adaptive thinking + `effort: low`. The system
prompt is cached (5-min TTL), so repeat generations within 5 minutes pay
~0.1× input cost. Rough per-disc cost on a fresh cache: ~$0.02–$0.05; on a
warm cache: ~$0.005.

Switch to a cheaper model (Sonnet 4.6 or Haiku 4.5) by editing the `MODEL`
constant in `discs/generator.py` if cost matters more than quality.

## Roadmap

- v2: Notion DB integration (inventory tracking) — blocked on MCP write
  permissions
- v2: eBay sold-listings comp lookup (price band suggestion)
- v3: eBay API auto-posting (Sell API + OAuth)
- v4: Batch mode — JSON file of N discs → N listings
