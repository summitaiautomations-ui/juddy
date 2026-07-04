# Pond Disc Hunter — Card Generator

Self-contained page that produces "DISC FOUND" social cards for pond disc recoveries.

Open `index.html` in any browser (double-click, no server needed):

1. **Disc photo** — upload the recovery shot, drag on the preview to frame it, zoom slider to crop tighter.
2. **Disc name + flight numbers** — speed / glide / turn / fade. The turn and fade arrows redraw from the numbers.
3. **Recovery blurb** — the story text at the bottom of the panel.
4. **Logo** — a built-in POND DISC HUNTER text mark is drawn by default; upload a PNG of the real logo to replace it.
5. **Download PNG** — exports at 2000 × 1600 (landscape) or 1080 × 1920 (vertical).

Fields persist in the browser between sessions (localStorage). "Reset fields" restores the defaults.

## Vertical video slides (Reels / Shorts / TikTok)

Switch **Orientation** to *Vertical — 1080 × 1920* to export a 9:16 slide that
drops straight into a vertical video edit:

- The photo is **full-bleed** — it fills the whole frame instead of a top band.
  Drag/zoom to put the disc in the upper half.
- Card content (DISC FOUND, flight numbers, arrows, story) overlays a dark
  gradient scrim on the lower half.
- Everything is kept inside platform **safe zones** — clear of the top ~140px
  (usernames/tabs), bottom ~270px (caption + music UI), and right ~130px
  (like/comment/share rail) — so nothing gets covered when posted.

From the command line, add `--vertical`:

```
node make-card.mjs photo.jpg --vertical --name "GATEWAY BLADE" \
  --speed 9 --glide 5 --turn 0 --fade 3 --story "..." --out slide.png
```

## Fully automatic cards (make-card.mjs)

`make-card.mjs` composites a finished card from the command line — used by Claude
to build cards from photos uploaded to `/photos`:

```
node make-card.mjs photo.jpg --name "GATEWAY BLADE" \
  --speed 9 --glide 5 --turn 0 --fade 3 \
  --story "..." --zoom 1.2 --out card.png
```

Add `--unknown` for the Mystery Disc treatment (grey "?" stats, wilted arrows)
and `--vertical` for the 1080 × 1920 video slide.
Requires Playwright + Chromium (preinstalled in the Claude remote environment).

## Mystery disc mode + sad trombone

The generator has a "Mystery disc" checkbox for finds with no readable stamp:
grey palette, "?" flight numbers, arrows that droop in defeat — and it plays a
synthesized sad-gameshow-trombone (also available via the 🎺 button).
