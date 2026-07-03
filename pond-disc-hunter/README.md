# Pond Disc Hunter — Card Generator

Self-contained page that produces "DISC FOUND" social cards for pond disc recoveries.

Open `index.html` in any browser (double-click, no server needed):

1. **Disc photo** — upload the recovery shot, drag on the preview to frame it, zoom slider to crop tighter.
2. **Disc name + flight numbers** — speed / glide / turn / fade. The turn and fade arrows redraw from the numbers.
3. **Recovery blurb** — the story text at the bottom of the panel.
4. **Logo** — a built-in POND DISC HUNTER text mark is drawn by default; upload a PNG of the real logo to replace it.
5. **Download PNG** — exports at 2000 × 1600.

Fields persist in the browser between sessions (localStorage). "Reset fields" restores the defaults.

## Fully automatic cards (make-card.mjs)

`make-card.mjs` composites a finished card from the command line — used by Claude
to build cards from photos uploaded to `/photos`:

```
node make-card.mjs photo.jpg --name "GATEWAY BLADE" \
  --speed 9 --glide 5 --turn 0 --fade 3 \
  --story "..." --zoom 1.2 --out card.png
```

Add `--unknown` for the Mystery Disc treatment (grey "?" stats, wilted arrows).
Requires Playwright + Chromium (preinstalled in the Claude remote environment).

## Mystery disc mode + sad trombone

The generator has a "Mystery disc" checkbox for finds with no readable stamp:
grey palette, "?" flight numbers, arrows that droop in defeat — and it plays a
synthesized sad-gameshow-trombone (also available via the 🎺 button).
