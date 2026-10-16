#!/usr/bin/env python3
"""Print-ready BLACK & WHITE disc labels for Avery 5160 / 8160 (1" x 2-5/8", 30 per sheet, 3 cols x 10 rows).
Usage:
  python3 scripts/disc-pics/make-labels-5160.py 490 491 492      # specific ids
  python3 scripts/disc-pics/make-labels-5160.py 490-500          # a range
  python3 scripts/disc-pics/make-labels-5160.py new              # last 12 available
  python3 scripts/disc-pics/make-labels-5160.py 490-500 --auction   # AUCTION bar
  python3 scripts/disc-pics/make-labels-5160.py bin:Innova bin:Discraft   # storage-bin labels
  python3 scripts/disc-pics/make-labels-5160.py 510-520 --start=3   # start at slot 3 of a partly used sheet, then keep filling
  python3 scripts/disc-pics/make-labels-5160.py 578-587 --layout=1-12,25-30   # only these slots on each sheet (one range list per sheet, ';' between sheets)
  python3 scripts/disc-pics/make-labels-5160.py 501 --slot=30   # one label per sheet in slot 30 (slots run left->right, top->bottom)
Writes labels-5160.html in repo root. Open in Safari/Chrome, Cmd+P,
paper US Letter, margins None, scale 100%, no headers/footers.
"""
import csv, sys, re, html, os

AUCTION = '--auction' in sys.argv
SLOT = None
START = 1
LAYOUT = None
args = []
for a in sys.argv[1:]:
    if a.startswith('--slot='): SLOT = int(a.split('=')[1])
    elif a.startswith('--start='): START = int(a.split('=')[1])
    elif a.startswith('--layout='):
        LAYOUT = []
        for sheet in a.split('=')[1].split(';'):
            sl = []
            for part in sheet.split(','):
                if '-' in part: lo, hi = part.split('-'); sl += list(range(int(lo), int(hi) + 1))
                elif part: sl.append(int(part))
            LAYOUT.append(sl)
    elif not a.startswith('--'): args.append(a)
BINS = [a[4:] for a in args if a.startswith('bin:')]
args = [a for a in args if not a.startswith('bin:')]

def flight(notes):
    m = re.search(r'Flight\s+(-?[0-9.]+)/(-?[0-9.]+)/(-?[0-9.]+)/(-?[0-9.]+)', notes)
    return m.groups() if m else ('', '', '', '')

def dtype(notes):
    n = notes.lower()
    for k in ('distance driver', 'fairway driver', 'hybrid driver', 'midrange', 'putt & approach', 'putter', 'approach'):
        if k in n: return k
    return ''

rows = list(csv.reader(open('disc-pics-data/sheet.csv')))
hdr = rows[0]
discs = [dict(zip(hdr, r)) for r in rows[1:] if len(r) == len(hdr)]

ids = set()
for a in args:
    if a == 'new':
        av = sorted([d for d in discs if d['status'] == 'available' and d['id'].isdigit()], key=lambda d: int(d['id']))
        ids |= {d['id'] for d in av[-12:]}
    elif re.fullmatch(r'\d+-\d+', a):
        lo, hi = a.split('-'); ids |= {str(i) for i in range(int(lo), int(hi) + 1)}
    else:
        ids.add(a)
ORDER = [a for a in args if a.isdigit()]
if ORDER and len(ORDER) == len(args):  # explicit ids only: keep the order given
    sel = sorted([d for d in discs if d['id'] in ids], key=lambda d: ORDER.index(d['id']))
else:
    sel = sorted([d for d in discs if d['id'] in ids], key=lambda d: int(d['id']))
if not sel and not BINS:
    sys.exit('no discs matched')

def bin_label(name):
    return f'<div class="lbl bin"><div class="binname">{html.escape(name)}</div></div>'

def label(d):
    e = html.escape
    s, g, t, f = flight(d['notes'])
    plastic = d['plastic'] if d['plastic'] and d['plastic'].lower() != 'unknown' else ''
    sub = ' · '.join(x for x in [plastic, d['color'], dtype(d['notes'])] if x)
    w = d['scale_weight_g'] if d['scale_weight_g'] not in ('', 'unknown') else d['stamped_weight_g']
    w = f'{w}g' if w and w != 'unknown' else '—'
    cond = d['condition'] if d['condition'] not in ('', 'unknown') else '—'
    ink = 'ink' if 'ink on back' in d['notes'].lower() else ('no ink' if 'no ink' in d['notes'].lower() else '')
    name = e(f"{d['brand']} {d['mold']}".strip())
    fl = ''.join(f'<i>{e(x) or "&nbsp;"}</i>' for x in (s, g, t, f))
    return f'''<div class="lbl">
  <div class="r1"><b class="num">#{e(d['id'])}</b><span class="name">{name}</span><b class="price">${e(d['price_usd'])}</b></div>
  <div class="sub">{e(sub)}</div>
  <div class="r3"><span class="fl">{fl}</span><b class="wt">{e(w)}</b></div>
  <div class="r4"><span>Cond {e(cond)}/10{(' · ' + ink) if ink else ''}</span><span class="dd">{'AUCTION' if AUCTION else 'DISC DIVER'}</span></div>
</div>'''

N = 30
BLANK = '<div class="lbl"></div>'
items = [BLANK] * (START - 1) + [label(d) for d in sel] + [bin_label(b) for b in BINS]
pages = []
if LAYOUT:
    q = list(items)
    for slots in LAYOUT:
        if not q: break
        cells = [BLANK] * N
        for sl in slots:
            if q: cells[sl - 1] = q.pop(0)
        pages.append('<div class="page">' + ''.join(cells) + '</div>')
elif SLOT:
    for it in items:
        cells = [BLANK] * N
        cells[SLOT - 1] = it
        pages.append('<div class="page">' + ''.join(cells) + '</div>')
else:
    for i in range(0, len(items), N):
        pages.append('<div class="page">' + ''.join(items[i:i+N]) + '</div>')

CSS = '''
@page { size: letter; margin: 0; }
* { box-sizing: border-box; }
body { margin: 0; font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; color: #111; }
.page { width: 8.5in; height: 11in; padding: 0.5in 0 0 0.1875in; page-break-after: always; display: grid;
  grid-template-columns: repeat(3, 2.625in); grid-template-rows: repeat(10, 1in); column-gap: 0.125in; }
.lbl { width: 2.625in; height: 1in; padding: 0.07in 0.13in 0.06in; display: flex; flex-direction: column; overflow: hidden; }
.r1 { display: flex; align-items: baseline; gap: 4pt; border-bottom: 0.75pt solid #111; padding-bottom: 1pt; }
.num { font-size: 13pt; letter-spacing: -.3px; }
.name { flex: 1; font-size: 9pt; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.price { font-size: 12pt; }
.sub { font-size: 6.5pt; margin-top: 1.5pt; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.r3 { display: flex; align-items: center; gap: 4pt; margin-top: 2.5pt; }
.fl { display: flex; gap: 2.5pt; flex: 1; }
.fl i { font-style: normal; flex: 1; text-align: center; border: 0.75pt solid #111; border-radius: 2pt; font-size: 9pt; font-weight: 700; line-height: 1.35; }
.wt { font-size: 10pt; min-width: 34pt; text-align: right; }
.r4 { margin-top: auto; display: flex; justify-content: space-between; font-size: 6pt; }
.dd { letter-spacing: 1.2px; }
.bin { justify-content: center; align-items: center; }
.binname { font-size: 18pt; font-weight: 700; text-align: center; line-height: 1.05; }
@media screen { body { background: #888; } .page { background: #fff; margin: 12px auto; box-shadow: 0 0 8px #0006; } .lbl { outline: 1px dashed #bbb; } }
'''
open('labels-5160.html', 'w').write(f'<!doctype html><meta charset="utf-8"><title>Disc Diver labels (Avery 5160)</title><style>{CSS}</style>{"".join(pages)}')
print(f'wrote labels-5160.html: {len(sel) + len(BINS)} labels on {len(pages)} sheet(s)')
