"""Does the exact (viewer hero x opponent hero) pair beat the pooled opponent effect,
now that STRATZ supplies population-scale pair counts?"""
import json, glob, pickle, collections, statistics as st, math

# assemble POSITION_1 'vs' rows from the per-hero cache
rows=[]
for f in glob.glob('raw/lo_POSITION_1_vs_*.json'):
    d=json.load(open(f))
    rows += ((d.get('data') or {}).get('heroStats') or {}).get('laneOutcome') or []
print(f"POSITION_1 vs pair-rows loaded: {len(rows)}  observations: {sum(x['matchCount'] or 0 for x in rows):,}")

def tables(min_pair):
    by1=collections.defaultdict(list)
    for x in rows:
        if (x['matchCount'] or 0) >= min_pair: by1[x['heroId1']].append(x)
    pair={}; agg=collections.defaultdict(lambda:[0.,0])
    for a,g in by1.items():
        n=sum(x['matchCount'] for x in g)
        if n < 3000: continue
        base=sum(x['csCount'] or 0 for x in g)/n
        for x in g:
            e=(x['csCount'] or 0)/x['matchCount']-base
            pair[(a,x['heroId2'])]=(e, x['matchCount'])
            agg[x['heroId2']][0]+=e*x['matchCount']; agg[x['heroId2']][1]+=x['matchCount']
    pooled={h:s/n for h,(s,n) in agg.items() if n>=3000}
    return pooled, pair

R=[r for r in pickle.load(open('metrics.pkl','rb'))
   if r['bucket']=='STANDARD' and r['role']=='Carry' and r['shape']=='2v2'
   and r.get('last_hits_at_10') is not None]
print(f"validation rows (Carry STANDARD 2v2): {len(R)}")

for min_pair, pair_gate in ((100,300),(100,800),(50,150)):
    pooled, pair = tables(min_pair)
    def E_pool(r):
        v=[pooled.get(h) for h in r['opps']]
        return None if any(x is None for x in v) else sum(v)
    def E_pair(r):
        tot=0.
        for h in r['opps']:
            p=pair.get((r['hero'],h))
            if p and p[1] >= pair_gate: tot += p[0]
            elif pooled.get(h) is not None: tot += pooled[h]      # fall back to pooled
            else: return None
        return tot
    def E_pair_strict(r):
        tot=0.
        for h in r['opps']:
            p=pair.get((r['hero'],h))
            if not p or p[1] < pair_gate: return None
            tot += p[0]
        return tot
    seq=collections.defaultdict(list)
    for r in R: seq[r['account']].append(r)
    res=collections.defaultdict(list); n=0; strict_ok=0
    for a,rs in seq.items():
        rs=sorted(rs,key=lambda r:(r['started'] or 0,r['match_id']))
        for i,r in enumerate(rs):
            pr=rs[max(0,i-20):i]
            if len(pr)<5: continue
            ep=E_pool(r); q=[E_pool(x) for x in pr]; q=[z for z in q if z is not None]
            if ep is None or len(q)<3: continue
            n+=1
            b=st.median(x['last_hits_at_10'] for x in pr)
            res['A'].append(r['last_hits_at_10']-b)
            res['pooled'].append(r['last_hits_at_10']-(b+ep-st.median(q)))
            e2=E_pair(r); q2=[E_pair(x) for x in pr]; q2=[z for z in q2 if z is not None]
            res['pair_backoff'].append(r['last_hits_at_10']-(b+(e2-st.median(q2) if e2 is not None and len(q2)>=3 else ep-st.median(q))))
            if E_pair_strict(r) is not None: strict_ok+=1
    vA=st.pvariance(res['A'])
    print(f"\n  min_pair={min_pair} pair_gate={pair_gate}: pooled heroes={len(pooled)} pair cells={len(pair)} "
          f"| n={n} strict-pairwise coverage={100*strict_ok/n:.1f}%")
    for k in ('pooled','pair_backoff'):
        print(f"      {k:<14} residual variance reduction = {100*(1-st.pvariance(res[k])/vA):+6.2f}%   "
              f"MAE {st.fmean(abs(x) for x in res[k]):.3f} (A={st.fmean(abs(x) for x in res['A']):.3f})")
