#!/usr/bin/env python3
"""Rebuild docs/testimonials/list.json from the images in that folder,
keeping any manual text-quote entries already in list.json.

Drop cropped screenshot images (jpg/png/webp) into docs/testimonials/,
run this, and the storefront's "Reunited" section shows them. The section
stays hidden while there is nothing to show.

Optional caption for an image: a same-named .txt (mike.jpg + mike.txt).
"""
import json, os, glob
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "docs", "testimonials")
LIST = os.path.join(D, "list.json")

# keep existing text-quote testimonials
quotes = []
if os.path.exists(LIST):
    try:
        for it in json.load(open(LIST)):
            if isinstance(it, dict) and it.get("quote"):
                quotes.append(it)
    except Exception:
        pass

imgs = []
for ext in ("jpg", "jpeg", "png", "webp"):
    for p in sorted(glob.glob(os.path.join(D, f"*.{ext}"))):
        name = os.path.basename(p)
        cap = os.path.splitext(p)[0] + ".txt"
        imgs.append({"img": name, "name": open(cap).read().strip()} if os.path.exists(cap) else name)

items = imgs + quotes            # real screenshots first, then text quotes
json.dump(items, open(LIST, "w"), indent=0, ensure_ascii=False)
print(f"wrote {len(imgs)} image + {len(quotes)} quote testimonial(s)")
