#!/usr/bin/env python3
"""Track the post-sale workflow (buyer / paid / shipped) for sold discs.

The website only cares whether a disc is available/claimed/sold. Once a disc
sells, the *fulfillment* side -- who bought it, did they pay, did we ship --
lives here in disc-pics-data/orders.csv, and gets rendered into the friendly
'Disc Diver Sales Tracker.xlsx' by make-tracker.py.

Usage:
  python3 scripts/disc-pics/track.py paid 010            # mark #010 paid
  python3 scripts/disc-pics/track.py shipped 010         # mark #010 shipped
  python3 scripts/disc-pics/track.py shipped 010 --tracking 9400111899...
  python3 scripts/disc-pics/track.py buyer 048 "Joe Miller"
  python3 scripts/disc-pics/track.py unpaid 010          # undo paid
  python3 scripts/disc-pics/track.py unshipped 010       # undo shipped

Any id you touch is added to orders.csv automatically if it isn't there yet.
Marking something paid/shipped also flags it 'sold' in the inventory (via
mark.py) so the storefront and the tracker never drift apart.

After editing, run make-tracker.py to rebuild the spreadsheet, then sync.sh.
"""
import csv, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ORDERS = os.path.join(ROOT, "disc-pics-data", "orders.csv")
FIELDS = ["id", "buyer", "sold_date", "paid", "shipped", "tracking",
          "order_notes", "desc", "amount"]


def load():
    if not os.path.exists(ORDERS):
        return []
    with open(ORDERS, newline="") as f:
        return list(csv.DictReader(f))


def save(rows):
    rows.sort(key=lambda r: r["id"])
    with open(ORDERS, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(rows)


def get(rows, oid):
    for r in rows:
        if r["id"] == oid:
            return r
    r = {k: "" for k in FIELDS}
    r["id"] = oid
    r["paid"] = r["shipped"] = "no"
    rows.append(r)
    return r


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    cmd = argv[0].lower()
    oid = argv[1].zfill(3)
    rows = load()
    r = get(rows, oid)

    if cmd == "paid":
        r["paid"] = "yes"
    elif cmd == "unpaid":
        r["paid"] = "no"
    elif cmd == "shipped":
        r["shipped"] = "yes"
        if "--tracking" in argv:
            r["tracking"] = argv[argv.index("--tracking") + 1]
    elif cmd == "unshipped":
        r["shipped"] = "no"
    elif cmd == "buyer":
        r["buyer"] = argv[2] if len(argv) > 2 else ""
    else:
        sys.exit(f"unknown command '{cmd}' (paid|unpaid|shipped|unshipped|buyer)")

    save(rows)

    # keep inventory in step: anything with an order is sold
    if cmd in ("paid", "shipped", "buyer"):
        try:
            subprocess.run([sys.executable,
                            os.path.join(os.path.dirname(__file__), "mark.py"),
                            "sold", oid], check=False)
        except Exception:
            pass

    print(f"  {oid}: buyer={r['buyer'] or '-'} paid={r['paid']} "
          f"shipped={r['shipped']} tracking={r['tracking'] or '-'}")
    print("Done. Run make-tracker.py to rebuild the spreadsheet, then sync.sh.")


if __name__ == "__main__":
    main(sys.argv[1:])
