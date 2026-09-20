"""Worked post-match examples from the STRATZ-sourced parameter set."""
import json, pickle, collections, statistics as st

H={h['id']:h['displayName'] for h in json.load(open(
 '/Users/nikanakamanifesto/Documents/GitHub/dota-report-card/.local/stratz-probe/deep-research-2026-09-14/raw/constants.json'
))['data']['constants']['heroes']}
LO=json.load(open('laneoutcome_all.json'))
HS={(x['heroId'],x['position'],x['time']):x for x in json.load(open('herostats_pop.json'))}
ROWS=pickle.load(open('metrics.pkl','rb'))
POS={'Carry':'POSITION_1','Mid':'POSITION_2','Offlane':'POSITION_3'}
SCALE={'Carry':0.75,'Mid':0.78,'Offlane':0.72}       # slope(ours ~ stratz), §Replication

def table(pos,min_pair=20,min_tot=500):
    by1=collections.defaultdict(list)
    for x in LO[f"{pos}|vs"]:
        if (x['matchCount'] or 0)>=min_pair: by1[x['heroId1']].append(x)
    agg=collections.defaultdict(lambda:[0.,0])
    for a,g in by1.items():
        n=sum(x['matchCount'] for x in g)
        if n<3000: continue
        base=sum(x['csCount'] or 0 for x in g)/n
        for x in g:
            e=(x['csCount'] or 0)/x['matchCount']-base
            agg[x['heroId2']][0]+=e*x['matchCount']; agg[x['heroId2']][1]+=x['matchCount']
    return {h:s/n for h,(s,n) in agg.items() if n>=min_tot}
T={r:table(p) for r,p in POS.items()}
HP=lambda r:(HS.get((r['hero'],r['pos'],10)) or {})

def env(r):
    t=T[r['role']]
    if r['shape'] not in ('2v2','1v1') or any(h not in t for h in r['opps']): return None
    return SCALE[r['role']]*sum(t[h] for h in r['opps'])

# thresholds per role from the corpus distribution of env
TH={}
for role in POS:
    v=sorted(x for x in (env(r) for r in ROWS
             if r['bucket']=='STANDARD' and r['role']==role) if x is not None)
    TH[role]=(v[int(.20*(len(v)-1))], v[int(.80*(len(v)-1))])
print("Frozen 20/60/20 thresholds on the STRATZ-sourced CS score:")
for r,(a,b) in TH.items(): print(f"   {r:<8} DIFFICULT <= {a:+.2f} CS   FAVOURABLE >= {b:+.2f} CS")

def label(r):
    e=env(r)
    if e is None: return 'UNAVAILABLE', None
    lo,hi=TH[r['role']]
    return ('DIFFICULT' if e<=lo else 'FAVOURABLE' if e>=hi else 'TYPICAL'), e

# build per-account chronology and emit example cards
seq=collections.defaultdict(list)
for r in ROWS:
    if r['bucket']=='STANDARD' and r['role'] in POS: seq[(r['account'],r['role'])].append(r)

def card(r, prior):
    b=st.median(x['last_hits_at_10'] for x in prior)
    lab,e=label(r)
    hp=HP(r).get('cs') if HP(r).get('matchCount',0)>=300 else None
    php=[ (HS.get((x['hero'],x['pos'],10)) or {}).get('cs') for x in prior]
    php=[z for z in php if z is not None]
    dh=(hp-st.median(php)) if hp is not None and len(php)>=3 else 0.0
    pe=[x for x in (env(x) for x in prior) if x is not None]
    de=(e-st.median(pe)) if e is not None and len(pe)>=3 else 0.0
    adj=b+dh+de
    d=r['last_hits_at_10']-adj
    sd=11.1
    state='ABOVE' if d>=0.35*sd else ('BELOW' if d<=-0.35*sd else 'IN_LINE')
    return dict(match=r['match_id'], role=r['role'], hero=H.get(r['hero'],r['hero']),
                opps=[H.get(h,h) for h in r['opps']], allies=[H.get(h,h) for h in r['allies']],
                cs=r['last_hits_at_10'], base=round(b,1), dh=round(dh,2), de=round(de,2),
                adj=round(adj,1), delta=round(d,1), lab=lab, state=state, win=r['win'],
                nw10=r['net_worth_at_10'], d10=r['deaths_before_10'])

WANTED=[('DIFFICULT','ABOVE',False,'Carry'),('FAVOURABLE','BELOW',True,'Carry'),
        ('TYPICAL','ABOVE',True,'Mid'),('DIFFICULT','IN_LINE',False,'Offlane'),
        ('FAVOURABLE','ABOVE',True,'Offlane'),('DIFFICULT','BELOW',False,'Mid'),
        ('TYPICAL','BELOW',True,'Carry')]
want={k:None for k in WANTED}
allc=[]
for k,rs in seq.items():
    rs=sorted(rs,key=lambda r:(r['started'] or 0,r['match_id']))
    for i,r in enumerate(rs):
        pr=rs[max(0,i-20):i]
        if len(pr)<5 or r.get('last_hits_at_10') is None: continue
        c=card(r,pr); allc.append(c)
seen=set()
for c in allc:
    key=(c['lab'],c['state'],c['win'],c['role'])
    if key in want and want[key] is None and c['match'] not in seen and abs(c['dh'])<6:
        want[key]=c; seen.add(c['match'])
import statistics as _st
dh=[abs(c['dh']) for c in allc]; de=[abs(c['de']) for c in allc]
print(f"\nADJUSTMENT MAGNITUDES over {len(allc)} comparable observations (CS@10):")
q=lambda v,p: sorted(v)[int(p*(len(v)-1))]
print(f"   |hero adj|: p50={q(dh,.5):.2f} p90={q(dh,.9):.2f} p99={q(dh,.99):.2f} max={max(dh):.2f}  "
      f"share >6 CS = {100*sum(1 for x in dh if x>6)/len(dh):.2f}%  >10 CS = {100*sum(1 for x in dh if x>10)/len(dh):.2f}%")
print(f"   |lane adj|: p50={q(de,.5):.2f} p90={q(de,.9):.2f} p99={q(de,.99):.2f} max={max(de):.2f}  "
      f"share >6 CS = {100*sum(1 for x in de if x>6)/len(de):.2f}%")
print("\n" + "="*96)
for k,c in want.items():
    if c is None: print(f"  (no example found for {k})"); continue
    print(f"\n[{c['lab']} / {c['state']} / {'WIN' if c['win'] else 'LOSS'}]  match {c['match']}  {c['role']} {c['hero']}")
    print(f"   lane: {c['hero']}" + (f" + {'/'.join(c['allies'])}" if c['allies'] else " (solo)") +
          f"  vs  {'/'.join(c['opps'])}")
    print(f"   CS@10 actual={c['cs']}   personal baseline={c['base']}   hero adj={c['dh']:+.2f}   "
          f"lane adj={c['de']:+.2f}   adjusted expectation={c['adj']}   delta={c['delta']:+.1f}")
    print(f"   (nw@10={c['nw10']}, deaths<10={c['d10']})")
