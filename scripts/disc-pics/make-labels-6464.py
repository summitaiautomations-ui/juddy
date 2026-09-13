#!/usr/bin/env python3
"""Print-ready BLACK & WHITE disc labels (no fills, ink-saving) for Avery 6464 (3-1/3" x 4", 6 per sheet, 2 cols x 3 rows).
Usage:
  python3 scripts/disc-pics/make-labels-6464.py 490 491 492      # specific ids
  python3 scripts/disc-pics/make-labels-6464.py 490-500          # a range
  python3 scripts/disc-pics/make-labels-6464.py new              # last 12 available
  python3 scripts/disc-pics/make-labels-6464.py 490-500 --auction   # AUCTION bar
  python3 scripts/disc-pics/make-labels-6464.py bin:Innova bin:Discraft   # storage-bin labels
  python3 scripts/disc-pics/make-labels-6464.py 501 --slot=6   # one label per sheet, in slot 6 (bottom right) - reuse partial sheets
Writes labels-6464.html in repo root. Open in Safari/Chrome, Cmd+P,
paper US Letter, margins None, scale 100%, no headers/footers.
"""
import csv, sys, re, html, os

AUCTION = '--auction' in sys.argv
SLOT = None
args = []
for a in sys.argv[1:]:
    if a.startswith('--slot='): SLOT = int(a.split('=')[1])
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
sel = sorted([d for d in discs if d['id'] in ids], key=lambda d: int(d['id']))
if not sel and not BINS:
    sys.exit('no discs matched')

def bin_label(name):
    return f'<div class="lbl bin"><div class="binname">{html.escape(name)}</div><div class="binsub">DISC DIVER</div></div>'

def label(d):
    e = html.escape
    s, g, t, f = flight(d['notes'])
    plastic = d['plastic'] if d['plastic'] and d['plastic'].lower() != 'unknown' else ''
    sub = ' · '.join(x for x in [plastic, d['color'], dtype(d['notes'])] if x)
    w = d['scale_weight_g'] if d['scale_weight_g'] not in ('', 'unknown') else d['stamped_weight_g']
    w = f'{w}g' if w and w != 'unknown' else '—'
    cond = d['condition'] if d['condition'] not in ('', 'unknown') else '—'
    ink = 'ink on back' if 'ink on back' in d['notes'].lower() else ('no ink' if 'no ink' in d['notes'].lower() else '')
    bar = 'AUCTION' if AUCTION else 'ON SITE'
    name = e(f"{d['brand']} {d['mold']}".strip())
    return f'''<div class="lbl">
  <div class="top"><div class="num">#{e(d['id'])}</div><div class="pr"><div class="dd">DISC DIVER</div><div class="price">${e(d['price_usd'])}</div></div></div>
  <div class="name">{name}</div>
  <div class="sub">{e(sub)}</div>
  <div class="fl">
    <div><span>Speed</span><b>{e(s)}</b></div><div><span>Glide</span><b>{e(g)}</b></div>
    <div><span>Turn</span><b>{e(t)}</b></div><div><span>Fade</span><b>{e(f)}</b></div>
    <div class="wt"><span>Weight</span><b>{e(w)}</b></div>
  </div>
  <div class="bot"><div class="cond">Cond {e(cond)}/10{(' · ' + ink) if ink else ''}</div><div class="bar">{bar}</div></div>
</div>'''

items = [label(d) for d in sel] + [bin_label(b) for b in BINS]
pages = []
if SLOT:
    for it in items:
        cells = ['<div class="lbl"></div>'] * 6
        cells[SLOT - 1] = it
        pages.append('<div class="page">' + ''.join(cells) + '</div>')
else:
    for i in range(0, len(items), 6):
        pages.append('<div class="page">' + ''.join(items[i:i+6]) + '</div>')

CSS = '''
@page { size: letter; margin: 0; }
* { box-sizing: border-box; }
body { margin: 0; font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; color: #111; }
.page { width: 8.5in; height: 11in; padding: 0.5in 0 0 0.15625in; page-break-after: always; display: grid;
  grid-template-columns: 4in 4in; grid-template-rows: repeat(3, 3.3333in); column-gap: 0.1875in; }
.lbl { width: 4in; height: 3.3333in; padding: 0.2in 0.22in 0.18in; display: flex; flex-direction: column; overflow: hidden; }
.top { display: flex; justify-content: space-between; align-items: flex-start; }
.num { font-size: 46pt; font-weight: 700; line-height: 1; letter-spacing: -1px; }
.pr { text-align: right; }
.dd { font-size: 8pt; letter-spacing: 1.5px; color: #111; }
.price { font-size: 22pt; font-weight: 700; line-height: 1.1; }
.name { margin-top: 8pt; border-top: 1.5pt solid #111; padding-top: 6pt; font-size: 17pt; font-weight: 700; line-height: 1.1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sub { font-size: 10.5pt; color: #111; margin-top: 2pt; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fl { display: flex; gap: 5pt; margin-top: 8pt; }
.fl > div { flex: 1; text-align: center; border: 1pt solid #111; border-radius: 4pt; padding: 3pt 0; }
.fl > div.wt { flex: 1.25; }
.fl span { display: block; font-size: 7.5pt; color: #111; }
.fl b { display: block; font-size: 15pt; line-height: 1.1; }
.bot { margin-top: auto; display: flex; justify-content: space-between; align-items: center; }
.cond { font-size: 9pt; color: #111; }
.bar { color: #111; border: 1.5pt solid #111; font-size: 9pt; font-weight: 700; letter-spacing: 1.5px; padding: 3pt 10pt; border-radius: 3pt; }
.bin { justify-content: center; align-items: center; text-align: center; }
.binname { font-size: 44pt; font-weight: 700; letter-spacing: 1px; line-height: 1; }
.binsub { font-size: 10pt; letter-spacing: 3px; margin-top: 12pt; }
@media screen { body { background: #888; } .page { background: #fff; margin: 12px auto; box-shadow: 0 0 8px #0006; } .lbl { outline: 1px dashed #bbb; } }
'''
open('labels-6464.html', 'w').write(f'<!doctype html><meta charset="utf-8"><title>Disc Diver labels (Avery 6464)</title><style>{CSS}</style>{"".join(pages)}')
print(f'wrote labels-6464.html: {len(items)} labels on {len(pages)} sheet(s)')
