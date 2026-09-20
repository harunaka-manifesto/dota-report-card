"""PART 1B — does STRATZ `lane` leak realised behaviour, and does the ally term matter?"""
import json, glob, pickle, collections, statistics as st

H={h['id']:h['displayName'] for h in json.load(open(
 '/Users/nikanakamanifesto/Documents/GitHub/dota-report-card/.local/stratz-probe/deep-research-2026-09-14/raw/constants.json'
))['data']['constants']['heroes']}

# ---------- 1. how deterministic is the lane assignment given (hero, position)? -------------
rows=pickle.load(open('merged.pkl','rb'))
big=pickle.load(open('metrics.pkl','rb'))
print("=== 1. Lane assignment concentration given (hero, position) ===")
g=collections.defaultdict(collections.Counter)
for r in big: g[(r['hero'], r['pos'])][r['lane']] += 1
for pos in ('POSITION_1','POSITION_2','POSITION_3','POSITION_4','POSITION_5'):
    ks=[(k,v) for k,v in g.items() if k[1]==pos and sum(v.values())>=80]
    shares=[max(v.values())/sum(v.values()) for k,v in ks]
    print(f"  {pos}: {len(ks)} (hero,pos) cells  modal-lane share: median={st.median(shares):.3f} "
          f"p10={sorted(shares)[len(shares)//10]:.3f} min={min(shares):.3f}")
print("\n  Least-deterministic (hero, position) cells, n>=80:")
worst=sorted(((max(v.values())/sum(v.values()), k, v) for k,v in g.items() if sum(v.values())>=80))[:14]
for s,k,v in worst:
    top=", ".join(f"{a}:{100*b/sum(v.values()):.0f}%" for a,b in v.most_common(3))
    print(f"    {H.get(k[0],k[0]):<20} {k[1]:<12} n={sum(v.values()):<5} modal={s:.2f}  [{top}]")

# ---------- 2. early-lane physical presence, from cached ten-player event positions ---------
print("\n=== 2. Realised early presence in the assigned lane (ten-player probe cache) ===")
def phys(lane, rad):
    if lane=="MID_LANE": return "MID"
    if lane=="SAFE_LANE": return "BOT" if rad else "TOP"
    if lane=="OFF_LANE": return "TOP" if rad else "BOT"
    return None
pts=collections.defaultdict(list)     # physical lane -> early event coords
per=[]                                # (hero, pos, phys, [coords])
for f in glob.glob('/Users/nikanakamanifesto/Documents/GitHub/dota-report-card/.local/stratz-probe/*/raw/*.json'):
    try: d=json.load(open(f))
    except Exception: continue
    for _,m in (d.get('data') or {}).items():
        if not isinstance(m,dict) or not isinstance(m.get('players'),list) or len(m['players'])!=10: continue
        for p in m['players']:
            s=p.get('stats')
            if not isinstance(s,dict) or p.get('lane') is None or p.get('position') is None: continue
            pl=phys(p['lane'], bool(p.get('isRadiant')))
            if pl is None: continue
            c=[]
            for key in ('killEvents','deathEvents','assistEvents','wards'):
                for e in (s.get(key) or []):
                    t=e.get('time')
                    if t is None or not (0 <= t < 600): continue
                    x,y=e.get('positionX'), e.get('positionY')
                    if x is None or y is None: continue
                    c.append((x,y))
            if c:
                pts[pl]+=c
                per.append((p['heroId'], p['position'], pl, c))
print(f"  players with >=1 positioned early event: {len(per)}")
cent={k:(st.fmean(x for x,y in v), st.fmean(y for x,y in v)) for k,v in pts.items()}
print("  data-derived lane centroids:", {k:(round(a),round(b)) for k,(a,b) in cent.items()})
def nearest(c):
    return min(cent, key=lambda k: (c[0]-cent[k][0])**2 + (c[1]-cent[k][1])**2)
share=collections.defaultdict(list)
for hero,pos,pl,c in per:
    if len(c) < 3: continue
    s=sum(1 for q in c if nearest(q)==pl)/len(c)
    share[(hero,pos)].append(s)
    share[('ALL',pos)].append(s)
for pos in ('POSITION_1','POSITION_2','POSITION_3','POSITION_4','POSITION_5'):
    v=share[('ALL',pos)]
    if v: print(f"  {pos}: mean presence-in-assigned-lane = {st.fmean(v):.3f}  (n={len(v)})")
cells=[(st.fmean(v), k, len(v)) for k,v in share.items() if k[0]!='ALL' and len(v)>=25 and k[1] in ('POSITION_4','POSITION_5')]
cells.sort()
print("\n  Lowest early-lane presence, support positions (n>=25) — the contamination candidates:")
for s,k,n in cells[:12]: print(f"    {H.get(k[0],k[0]):<20} {k[1]:<12} n={n:<4} presence={s:.3f}")
print("  Highest:")
for s,k,n in cells[-6:][::-1]: print(f"    {H.get(k[0],k[0]):<20} {k[1]:<12} n={n:<4} presence={s:.3f}")
