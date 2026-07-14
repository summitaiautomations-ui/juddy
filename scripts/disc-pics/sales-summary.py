#!/usr/bin/env python3
"""Print a quick Disc Diver sales recap from inventory.csv + orders.csv.

Juddy likes to SEE the running totals every time a sale is logged, so this
prints a compact "spreadsheet" to the terminal:
  * one row per buyer (order): # discs, paid?, shipped?, pay method, total
  * headline totals: discs sold, cash collected, still-owed, available count

orders.csv is PRIVATE (gitignored) -- it holds buyer names. This script only
READS the CSVs and prints; it never writes and never leaves the machine.

Usage:  python3 scripts/disc-pics/sales-summary.py
"""
import csv, os, re
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "disc-pics-data")


def rows(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return []
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def main():
    inv = {r["id"]: r for r in rows("inventory.csv")}
    orders = rows("orders.csv")

    def disc_price(i):
        d = inv.get(str(int(i))) if i.strip("0").isdigit() else inv.get(i)
        try:
            return float(d["price"])
        except (TypeError, ValueError, KeyError):
            return 0.0

    g = defaultdict(lambda: {"ids": [], "paid": set(), "ship": set(),
                             "via": set(), "notes": [], "amounts": []})
    for o in orders:
        b = (o.get("buyer") or "(unknown)").strip() or "(unknown)"
        x = g[b]
        x["ids"].append(o["id"])
        x["paid"].add((o.get("paid") or "no").lower())
        x["ship"].add((o.get("shipped") or "no").lower())
        if o.get("paid_via"):
            x["via"].add(o["paid_via"])
        x["notes"].append(o.get("order_notes") or "")
        x["amounts"].append((o.get("amount") or "").strip())

    def order_total(x):
        # 1) a "Paid $NN" in the notes is the authoritative order total
        for n in x["notes"]:
            m = re.search(r"[Pp]aid \$([\d.]+)", n)
            if m:
                return float(m.group(1)), True
        # 2) else sum per-disc: listed price, or the amount field for off-site
        tot = 0.0
        for i, amt in zip(x["ids"], x["amounts"]):
            p = disc_price(i)
            tot += p if p else (float(amt) if amt else 0.0)
        paid = x["paid"] == {"yes"}
        return tot, paid

    print("=" * 66)
    print("  DISC DIVER — SALES RECAP")
    print("=" * 66)
    print(f"  {'BUYER':20}{'#':>3}  {'PAID':4} {'SHIP':4} {'VIA':10} {'TOTAL':>8}")
    print("  " + "-" * 62)

    collected = owed = 0.0
    n_sold = n_toship = 0
    lines = []
    for b, x in g.items():
        tot, paid = order_total(x)
        pd = "yes" if x["paid"] == {"yes"} else "no"
        sh = "yes" if x["ship"] == {"yes"} else ("no" if x["ship"] == {"no"} else "part")
        n_sold += len(x["ids"])
        if pd == "yes":
            collected += tot
            if sh != "yes":
                n_toship += len(x["ids"])
        else:
            owed += tot
        via = "/".join(sorted(x["via"])) or "-"
        lines.append((paid, tot, b, len(x["ids"]), pd, sh, via))

    # paid first (biggest total on top), then unpaid
    for paid, tot, b, n, pd, sh, via in sorted(lines, key=lambda r: (not r[0], -r[1])):
        print(f"  {b:20}{n:>3}  {pd:4} {sh:4} {via:10} ${tot:>7.2f}")

    avail = sum(1 for d in inv.values() if d.get("status") == "available")
    print("  " + "-" * 62)
    print(f"  Discs sold: {n_sold}     Cash collected: ${collected:,.2f}")
    print(f"  Still owed (friends/pickup): ${owed:,.2f}"
          f"     To ship: {n_toship}")
    print(f"  Booked (paid+owed): ${collected+owed:,.2f}"
          f"     Still available: {avail}")
    print("=" * 66)


if __name__ == "__main__":
    main()
