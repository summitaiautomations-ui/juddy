#!/usr/bin/env python3
"""Crop a disc photo to a tight, centered square.

Detects the disc by its contrast against the surrounding background (sampled
from the image border), crops to it with a little padding, and squares the
result to SIZE x SIZE (default 900, matching the existing storefront photos).
Padding is filled with the sampled background color so it blends seamlessly.

Safe by design: if Pillow/numpy/scipy aren't installed, or detection is
uncertain, it either falls back to a sensible centered square or leaves the
photo untouched -- it never raises into the pipeline.

Usage:  crop-disc.py IMG [IMG ...]
Env:    DISC_CROP_SIZE (default 900), DISC_CROP=0 disables (handled by caller)
"""
import sys, os

try:
    from PIL import Image
    import numpy as np
    from scipy import ndimage
except Exception:
    sys.exit(0)  # optional deps missing -> skip quietly, like the other steps

SIZE = int(os.environ.get("DISC_CROP_SIZE", "900"))

def crop_one(path):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(int)
    h, w, _ = a.shape

    # Estimate the background color from a frame around the border.
    m = max(4, int(0.04 * min(h, w)))
    border = np.concatenate([a[:m].reshape(-1, 3), a[-m:].reshape(-1, 3),
                             a[:, :m].reshape(-1, 3), a[:, -m:].reshape(-1, 3)])
    bg = np.median(border, axis=0)

    # Disc = pixels that differ from the background; clean up thin bridges.
    dist = np.sqrt(((a - bg) ** 2).sum(axis=2))
    mask = ndimage.binary_opening(dist > 45, iterations=4)
    lbl, n = ndimage.label(mask)

    cx, cy = w / 2.0, h / 2.0
    best = None
    for i in range(1, n + 1):
        ys, xs = np.where(lbl == i)
        if len(xs) < 0.02 * h * w:                    # ignore small specks
            continue
        bx0, bx1, by0, by1 = xs.min(), xs.max(), ys.min(), ys.max()
        ar = (bx1 - bx0) / max(by1 - by0, 1)
        roundness = 1.0 if 0.6 < ar < 1.7 else 0.15   # disc is round; a bag edge is wide/short
        off = (((bx0 + bx1) / 2 - cx) / w) ** 2 + (((by0 + by1) / 2 - cy) / h) ** 2
        score = len(xs) * roundness / (1 + 4 * off)   # big, round, and central wins
        if best is None or score > best[0]:
            best = (score, bx0, bx1, by0, by1)

    if best is None:                                  # low-contrast disc: safe centered crop
        s = int(0.72 * min(h, w))
        x0, y0 = int(cx - s / 2), int(cy - s / 2)
        x1, y1 = x0 + s, y0 + s
    else:
        _, x0, x1, y0, y1 = best
        pad = int(0.09 * max(x1 - x0, y1 - y0))
        x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad

    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w - 1, x1), min(h - 1, y1)
    crop = im.crop((x0, y0, x1 + 1, y1 + 1))
    cw, ch = crop.size
    side = max(cw, ch)
    canvas = Image.new("RGB", (side, side), tuple(int(v) for v in bg))
    canvas.paste(crop, ((side - cw) // 2, (side - ch) // 2))
    canvas.resize((SIZE, SIZE), Image.LANCZOS).save(path, quality=90)

for p in sys.argv[1:]:
    try:
        crop_one(p)
    except Exception:
        pass  # never break the pipeline over a single photo
