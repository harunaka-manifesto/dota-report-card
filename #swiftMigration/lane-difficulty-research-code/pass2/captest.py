"""Does capping the total context adjustment cost accuracy?"""
import json, pickle, collections, statistics as st, math
LO=json.load(open('laneoutcome_all.json'))
HS={(x['heroId'],x['position'],x['time']):x for x in json.load(open('herostats_pop.json'))}
ROWS=pickle.load(open('metrics.pkl','rb'))
POS={'Carry':'POSITION_1','Mid':'POSITION_2','Offlane':'POSITION_3'}
SCALE={'Carry':0.75,'Mid':0.78,'Offlane':0.72}
def table(pos):
    by1=collections.defaultdict(list)
    for x in LO[f"{pos}|vs"]:
        if (x['matchCount'] or 0)>=20: by1[x['heroId1']].append(x)
    agg=collections.defaultdict(lambda:[0.,0])
    for a,g in by1.items():
        n=sum(x['matchCount'] for x in g)
        if n<3000: continue
        base=sum(x['csCount'] or 0 for x in g)/n
        for x in g:
            e=(x['csCount'] or 0)/x['matchCount']-base
            agg[x['heroId2']][0]+=e*x['matchCount']; agg[x['heroId2']][1]+=x['matchCount']
    return {h:s/n for h,(s,n) in agg.items() if n>=500}
T={r:table(p) for r,p in POS.items()}
for role in POS:
    pool=[r for r in ROWS if r['bucket']=='STANDARD' and r['role']==role and r.get('last_hits_at_10') is not None]
    seq=collections.defaultdict(list)
    for r in pool: seq[r['account']].append(r)
    def env(r):
        t=T[role]
        if r['shape'] not in ('2v2','1v1') or any(h not in t for h in r['opps']): return None
        return SCALE[role]*sum(t[h] for h in r['opps'])
    def hp(r):
        x=HS.get((r['hero'],r['pos'],10)) or {}
        return x.get('cs') if (x.get('matchCount') or 0)>=300 else None
    res=collections.defaultdict(list); n=0
    for a,rs in seq.items():
        rs=sorted(rs,key=lambda r:(r['started'] or 0,r['match_id']))
        for i,r in enumerate(rs):
            pr=rs[max(0,i-20):i]
            if len(pr)<5: continue
            e=env(r); h=hp(r)
            qe=[x for x in (env(x) for x in pr) if x is not None]
            qh=[x for x in (hp(x) for x in pr) if x is not None]
            if e is None or h is None or len(qe)<3 or len(qh)<3: continue
            n+=1
            b=st.median(x['last_hits_at_10'] for x in pr); y=r['last_hits_at_10']
            dh=h-st.median(qh); de=e-st.median(qe)
            res['A'].append(y-b)
            for cap in (None,10,8,6,5,4):
                if cap is None: a_=dh+de
                else: a_=max(-cap,min(cap,dh))+max(-cap*0.8,min(cap*0.8,de))
                res[f"cap={cap}"].append(y-(b+a_))
    vA=st.pvariance(res['A']); mA=st.fmean(abs(x) for x in res['A'])
    print(f"\n  {role} n={n} sdA={math.sqrt(vA):.2f}")
    for cap in (None,10,8,6,5,4):
        k=f"cap={cap}"
        print(f"     {k:<10} variance {100*(1-st.pvariance(res[k])/vA):+6.2f}%   MAE {100*(1-st.fmean(abs(x) for x in res[k])/mA):+6.2f}%")
