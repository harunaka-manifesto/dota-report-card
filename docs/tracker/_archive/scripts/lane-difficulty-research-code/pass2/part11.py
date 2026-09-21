"""PART 11 — does hero-pool drift corrupt the locked 10-point trend on raw baselines?"""
import json, pickle, collections, statistics as st

HS={(r['heroId'],r['position'],r['time']):r for r in json.load(open('herostats_pop.json'))}
ROWS=[r for r in pickle.load(open('metrics.pkl','rb')) if r['bucket']=='STANDARD']
FIELD={'last_hits_at_10':('cs',10),'net_worth_at_10':('networth',10)}

def hero_pop(r,f,t,minm=300):
    x=HS.get((r['hero'],r['pos'],t))
    if not x or (x.get('matchCount') or 0)<minm or x.get(f) is None: return None
    return x[f]

for tgt in FIELD:
    f,t=FIELD[tgt]
    for role in ('Carry','Mid','Offlane','Support'):
        pool=[r for r in ROWS if r['role']==role and r.get(tgt) is not None]
        seq=collections.defaultdict(list)
        for r in pool: seq[r['account']].append(r)
        raw_drift=[]; adj_drift=[]; hero_drift=[]; windows=0
        for a,rs in seq.items():
            rs=sorted(rs,key=lambda r:(r['started'] or 0,r['match_id']))
            pts=[]
            for i,r in enumerate(rs):
                pr=rs[max(0,i-20):i]
                if len(pr)<5: continue
                hp=[hero_pop(x,f,t) for x in pr]; hp=[z for z in hp if z is not None]
                if len(hp)<3: continue
                pts.append((st.median(x[tgt] for x in pr), st.median(hp)))
            for i in range(9,len(pts)):
                w=pts[i-9:i+1]; windows+=1
                raw_drift.append(w[-1][0]-w[0][0])
                hero_drift.append(w[-1][1]-w[0][1])
                adj_drift.append((w[-1][0]-w[-1][1])-(w[0][0]-w[0][1]))
        if windows<400: continue
        def corr(x,y):
            mx,my=st.fmean(x),st.fmean(y)
            return st.fmean([(p-mx)*(q-my) for p,q in zip(x,y)])/(st.pstdev(x)*st.pstdev(y))
        vr=st.pvariance(raw_drift); va=st.pvariance(adj_drift); vh=st.pvariance(hero_drift)
        flip=sum(1 for dr,da in zip(raw_drift,adj_drift) if dr*da<0)
        print(f"  {tgt:<18}{role:<9}windows={windows:<6} sd(raw 10-pt baseline drift)={vr**.5:8.2f}  "
              f"sd(hero-mix drift)={vh**.5:7.2f} ({100*vh/vr:4.1f}% of raw var)  "
              f"corr(raw,hero)={corr(raw_drift,hero_drift):+.3f}  sign-flip after adj={100*flip/windows:4.1f}%")
print("PART 11 — 10-point baseline drift, STANDARD")
