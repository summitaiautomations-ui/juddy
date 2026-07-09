#!/usr/bin/env python3
"""Rebuild docs/testimonials/list.json from images in that folder, keeping any
manual entries already in list.json (text quotes AND chat threads).

Screenshots (jpg/png/webp) in docs/testimonials/ become image cards. Optional
caption: a same-named .txt (mike.jpg + mike.txt).
"""
import json, os, glob
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "docs", "testimonials")
LIST = os.path.join(D, "list.json")

# keep manual entries (anything that isn't a plain image reference)
manual = []
if os.path.exists(LIST):
    try:
        for it in json.load(open(LIST)):
            if isinstance(it, dict) and ("quote" in it or "thread" in it):
                manual.append(it)
    except Exception:
        pass

imgs = []
for ext in ("jpg", "jpeg", "png", "webp"):
    for p in sorted(glob.glob(os.path.join(D, f"*.{ext}"))):
        name = os.path.basename(p)
        cap = os.path.splitext(p)[0] + ".txt"
        imgs.append({"img": name, "name": open(cap).read().strip()} if os.path.exists(cap) else name)

items = imgs + manual            # real screenshots first, then text/threads
json.dump(items, open(LIST, "w"), indent=0, ensure_ascii=False)
print(f"wrote {len(imgs)} image + {len(manual)} text/thread testimonial(s)")
