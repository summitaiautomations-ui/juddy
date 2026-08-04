#!/usr/bin/env python3
"""Generate print-ready disc labels from sheet.csv.
Usage:
  python3 scripts/disc-pics/make-labels.py 330 331 332 333   # specific lots
  python3 scripts/disc-pics/make-labels.py 330-345           # a range
  python3 scripts/disc-pics/make-labels.py new               # New-Arrival lots (last 20)
  python3 scripts/disc-pics/make-labels.py all               # every available disc
Writes labels.html in repo root; open it and hit Cmd+P (fits Avery 5160/8160, 30/sheet).
"""
import csv, sys, re, os, html

def flight_from_notes(notes):
    m=re.search(r'Flight\s+([0-9]+/[0-9]+/-?[0-9.]+/-?[0-9.]+)', notes)
    return m.group(1) if m else ""

def load():
    rows=list(csv.reader(open('disc-pics-data/sheet.csv')))
    hdr=rows[0]; return [dict(zip(hdr,r)) for r in rows[1:] if len(r)==len(hdr)]

def pick(discs, args):
    ids=set()
    for a in args:
        if a=='all':
            return [d for d in discs if d['status']=='available']
        if a=='new':
            avail=[d for d in discs if d['status']=='available' and d['id'].isdigit()]
            avail.sort(key=lambda d:int(d['id']))
            return avail[-20:]
        if '-' in a and all(p.isdigit() for p in a.split('-')):
            lo,hi=a.split('-'); ids|={str(i) for i in range(int(lo),int(hi)+1)}
        else:
            ids.add(a)
    return [d for d in discs if d['id'] in ids]

def label_html(d):
    flight=flight_from_notes(d['notes'])
    plastic=d['plastic'] if d['plastic'] and d['plastic'].lower()!='unknown' else ''
    sub=" · ".join(x for x in [d['brand'], plastic] if x)
    e=html.escape
    return f'''<div class="lbl">
      <div class="top"><span class="lot">#{e(d['id'])}</span><span class="mold">{e(d['mold'])}</span></div>
      <div class="brand">{e(sub)}</div>
      <div class="bot"><span class="flt">{e(flight) or '&mdash;'}</span><span class="meta">${e(d['price_usd'])} · {e(d['condition'])}/10 · {e(d['scale_weight_g'])}g</span></div>
    </div>'''

def main():
    args=sys.argv[1:] or ['new']
    discs=load()
    sel=pick(discs,args)
    sel=[d for d in sel if d['id'].isdigit()]
    sel.sort(key=lambda d:int(d['id']))
    body="".join(label_html(d) for d in sel)
    css='''
    @page{size:8.5in 11in;margin:0.5in 0.19in;}
    *{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,Arial,sans-serif;}
    body{width:8.11in;}
    .lbl{display:inline-block;vertical-align:top;width:2.625in;height:1in;padding:0.07in 0.12in;
      margin-right:0.125in;overflow:hidden;border:0.5px dashed #ccc;}
    .lbl:nth-child(3n){margin-right:0;}
    .top{display:flex;align-items:baseline;gap:5px;}
    .lot{font-size:15px;font-weight:800;color:#0a6;}
    .mold{font-size:15px;font-weight:800;letter-spacing:-.2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
    .brand{font-size:10.5px;color:#555;margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
    .bot{display:flex;justify-content:space-between;align-items:baseline;margin-top:3px;}
    .flt{font-size:17px;font-weight:900;font-variant-numeric:tabular-nums;letter-spacing:.5px;}
    .meta{font-size:9.5px;color:#666;}
    @media print{.lbl{border:none;}}
    '''
    out=f"<!doctype html><meta charset=utf-8><title>Disc Labels</title><style>{css}</style>{body}"
    open('labels.html','w').write(out)
    print(f"Wrote labels.html with {len(sel)} labels. Open it and press Cmd+P (Avery 5160/8160, 30 per sheet).")

if __name__=='__main__': main()
