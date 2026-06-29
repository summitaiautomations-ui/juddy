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

### Snap a pic (fastest)

```bash
discs/.venv/bin/python -m discs photo ~/Desktop/disc.jpg
```

Pass any image path. Supports HEIC (iPhone default) automatically via
pillow-heif. Claude Opus 4.8 vision identifies the disc — brand, mold,
plastic, weight (read from the rim), color, stamp condition, **back ink
(name/phone on the bottom of the disc)**, estimated sleeve rating,
category — then generates the listings in a single call.

Verify the identification block at the top before relying on the listing.
If the weight wasn't visible in the photo or the angle hid wear, the
extraction notes will say so.

**Tip for best identification:**
- Photograph the stamp side flat-on so the mold name + plastic are readable
- Include the rim where the weight is printed (usually opposite the stamp)
- Flip the disc and snap the back too if it has owner ink — otherwise the
  back-ink field will say "Not visible"
- Good lighting, plain background
- One disc per photo

### Batch a whole folder

Drop all the photos for a session into one folder, then:

```bash
discs/.venv/bin/python -m discs batch ~/Desktop/discs-to-list/
```

Processes every `.jpg/.jpeg/.png/.heic/.webp` in the folder — one Claude
call per disc, each saved as its own markdown file in `discs/output/`.
Failures are listed at the end; successful runs still save.

### Manual entry (when you don't have a photo)

```bash
discs/.venv/bin/python -m discs generate
```

Interactive prompts for brand, mold, plastic, weight, color, sleeve,
special run, notes.

### Output

Every command prints the same five labeled blocks:
- **eBay TITLE** (with character count vs. the 80-char limit)
- **eBay DESCRIPTION** (plain text, no HTML)
- **BST POST** (markdown for Reddit r/discexchange, DGCR BST forum, or the
  Marketplace Disc Golf app)
- **eBay CATEGORY** breadcrumb
- **COMP PRICING SEARCH** — paste straight into eBay → Advanced → Sold listings

**Automation built in:**
- Full output is auto-saved as markdown to `discs/output/<timestamp>_<mold>.md`
  (gitignored, kept locally on the Mac mini)
- The eBay title is auto-copied to your clipboard — open eBay → Sell and
  ⌘V it straight into the title field

## Costs

Uses Claude Opus 4.8 with adaptive thinking + `effort: low`. The system
prompt is cached (5-min TTL), so repeat generations within 5 minutes pay
~0.1× input cost. Rough per-disc cost on a fresh cache: ~$0.02–$0.05; on a
warm cache: ~$0.005.

Switch to a cheaper model (Sonnet 4.6 or Haiku 4.5) by editing the `MODEL`
constant in `discs/generator.py` if cost matters more than quality.

### Push to eBay as a draft

End-to-end: folder of disc photos → draft listing in your eBay Seller Hub
that you tap **Publish** on to make live.

```bash
discs/.venv/bin/python -m discs ebay-setup        # one-time OAuth + policies
discs/.venv/bin/python -m discs ebay-draft ~/Desktop/destroyer-172-yellow/
```

Folder layout:

```
destroyer-172-yellow/
  stamp.jpg     (front — primary photo)
  back.jpg      (back — source of truth for back ink)
  profile.jpg   (side profile)
  weight.jpg    (rim where weight is printed)
  price.txt     (optional: just the number, e.g. "25")
```

If `price.txt` is missing, the command prompts for a price.

See `discs/EBAY_SETUP.md` for the full one-time setup (developer account,
credentials, business policies).

## Roadmap

- v2: Notion DB integration (inventory tracking) — blocked on MCP write
  permissions
- v2: eBay sold-listings comp lookup (price band suggestion)
- v3: eBay auto-publish flag (currently draft-only — review before going live)
- v4: Batch mode for `ebay-draft` (parent folder of N disc folders)
