#!/usr/bin/env python3
"""Reads sales-log.csv, prints computed Disc Diver sales metrics as JSON."""
import csv, json, datetime, sys, os

HERE=os.path.dirname(os.path.abspath(__file__))
LOG=os.path.join(HERE,'sales-log.csv')

def num(x):
    x=(x or '').strip().replace('$','').replace(',','')
    try: return float(x)
    except: return 0.0

rows=list(csv.DictReader(open(LOG)))
tot_discs=tot_gross=tot_bonus=tot_net=0.0
by_channel={}
dated=[]
for r in rows:
    d=int(num(r['num_discs'])); g=num(r['gross_usd']); b=num(r['bonus_usd']); n=num(r['net_usd'])
    tot_discs+=d; tot_gross+=g; tot_bonus+=b; tot_net+=n
    ch=r['channel']
    c=by_channel.setdefault(ch,{'discs':0,'gross':0.0,'net':0.0})
    c['discs']+=d; c['gross']+=g; c['net']+=n
    try: dated.append(datetime.date.fromisoformat(r['date'].strip()))
    except: pass

# average per day: from first recorded sale to today
today=datetime.date.fromisoformat(os.environ.get('TODAY','2026-07-28'))
first=min(dated) if dated else today
span_days=max(1,(today-first).days+1)

out={
 'total_discs':int(tot_discs),
 'total_gross':round(tot_gross,2),
 'total_bonus':round(tot_bonus,2),
 'total_net':round(tot_net,2),
 'net_per_disc':round(tot_net/tot_discs,2) if tot_discs else 0,
 'first_sale':first.isoformat(),'today':today.isoformat(),'span_days':span_days,
 'avg_net_per_day':round(tot_net/span_days,2),
 'avg_discs_per_day':round(tot_discs/span_days,2),
 'by_channel':{k:{'discs':int(v['discs']),'gross':round(v['gross'],2),'net':round(v['net'],2)} for k,v in by_channel.items()},
 'num_events':len(rows),
}
print(json.dumps(out,indent=2))
