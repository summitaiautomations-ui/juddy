#!/usr/bin/env python3
"""Mark disc(s) as sold / claimed / available in both inventory CSVs.

The storefront reads `status` straight from sheet.csv: a disc set to
"claimed" or "sold" shows a stamp and hides its Claim button; "available"
brings it back.

Usage:
  python3 scripts/disc-pics/mark.py sold 017
  python3 scripts/disc-pics/mark.py claimed 023 041 042
  python3 scripts/disc-pics/mark.py available 017

Then run sync.sh to push (or it rides along with the next sync).
"""
import csv, os, sys

VALID = {"available", "claimed", "sold"}
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FILES = [  # path, id-column, status-column
    (os.path.join(ROOT, "disc-pics-data", "inventory.csv"), 0, 11),
    (os.path.join(ROOT, "disc-pics-data", "sheet.csv"), 1, 10),
]


def main(argv):
    if len(argv) < 2 or argv[0].lower() not in VALID:
        sys.exit(f"usage: mark.py <{'|'.join(sorted(VALID))}> <id> [id ...]")
    status = argv[0].lower()
    ids = {i.zfill(3) for i in argv[1:]}

    found = set()
    for path, idc, stc in FILES:
        with open(path, newline="") as f:
            rows = list(csv.reader(f))
        for r in rows[1:]:
            if len(r) > stc and r[idc] in ids:
                r[stc] = status
                found.add(r[idc])
        with open(path, "w", newline="") as f:
            csv.writer(f, quoting=csv.QUOTE_NONNUMERIC).writerows(rows)

    for i in sorted(ids):
        print(f"  {i}: {'-> ' + status if i in found else 'NOT FOUND'}")
    missing = ids - found
    if missing:
        sys.exit(f"warning: no such disc id(s): {', '.join(sorted(missing))}")
    print(f"Done. {len(found)} disc(s) set to '{status}'. Run sync.sh to push.")


if __name__ == "__main__":
    main(sys.argv[1:])
