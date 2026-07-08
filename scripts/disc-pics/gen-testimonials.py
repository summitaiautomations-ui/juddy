#!/usr/bin/env python3
"""Rebuild docs/testimonials/list.json from the images in that folder.

Drop cropped text-screenshot images (jpg/png/webp) into docs/testimonials/,
run this, and the storefront's "Reunited" section shows them automatically.
The section stays hidden while the folder is empty.

Optional captions: keep a same-named .txt next to an image (e.g. mike.txt
next to mike.jpg) containing a short name/quote; it renders under the image.
"""
import json, os, glob
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "docs", "testimonials")
imgs = sorted(f for ext in ("jpg","jpeg","png","webp")
              for f in glob.glob(os.path.join(D, f"*.{ext}")))
items = []
for p in imgs:
    name = os.path.basename(p)
    cap_path = os.path.splitext(p)[0] + ".txt"
    if os.path.exists(cap_path):
        items.append({"img": name, "name": open(cap_path).read().strip()})
    else:
        items.append(name)
with open(os.path.join(D, "list.json"), "w") as f:
    json.dump(items, f, indent=0)
print(f"wrote {len(items)} testimonial(s) to list.json")
