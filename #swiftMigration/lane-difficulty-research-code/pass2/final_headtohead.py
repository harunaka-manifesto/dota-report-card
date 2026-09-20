"""STRATZ-sourced lane-environment parameters vs our own corpus fit, in the real pipeline.
Also: coverage of the STRATZ pooled table over real lane-opponent slots."""
import json, pickle, collections, statistics as st, random, math

LO=json.load(open('laneoutcome_all.json'))
HS={(x['heroId'],x['position'],x['time']):x for x in json.load(open('herostats_pop.json'))}
ROWS=pickle.load(open('metrics.pkl','rb'))
POS={'Carry':'POSITION_1','Mid':'POSITION_2','Offlane':'POSITION_3'}

def pooled_table(pos, min_pair, min_tot):
    by1=collections.defaultdict(list)
    for x in LO[f"{pos}|vs"]:
        if (x['matchCount'] or 0) >= min_pair: by1[x['heroId1']].append(x)
    agg=collections.defaultdict(lambda:[0.,0])
    for a,g in by1.items():
        n=sum(x['matchCount'] for x in g)
        if n<3000: continue
        base=sum(x['csCount'] or 0 for x in g)/n
        for x in g:
            e=(x['csCount'] or 0)/x['matchCount']-base
            agg[x['heroId2']][0]+=e*x['matchCount']; agg[x['heroId2']][1]+=x['matchCount']
    return {h:s/n for h,(s,n) in agg.items() if n>=min_tot}

print("=== Coverage of the STRATZ pooled opponent table over real lane-opponent slots (one week of data) ===")
for role,pos in POS.items():
    R=[r for r in ROWS if r['bucket']=='STANDARD' and r['role']==role and r['shape'] in ('2v2','1v1')]
    for mp,mt in ((100,3000),(50,1500),(20,500)):
        T=pooled_table(pos,mp,mt)
        slots=[h for r in R for h in r['opps']]
        cov=sum(1 for h in slots if h in T)/len(slots)
        full=sum(1 for r in R if all(h in T for h in r['opps']))/len(R)
        print(f"  {role:<8} min_pair={mp:<4} min_tot={mt:<5} heroes={len(T):>3}  opponent slots covered={100*cov:5.1f}%  "
              f"matches fully covered={100*full:5.1f}%")

print("\n=== Head to head in the personal-baseline pipeline (CS@10, STANDARD, opponents only) ===")
def fit_ours(d,tgt,k=40.,iters=6):
    ys=[r[tgt] for r in d]; g=sum(ys)/len(ys); own={}; opp={}
    for _ in range(iters):
        b=lambda r: g+own.get(r['hero'],0.)+sum(opp.get(h,0.) for h in r['opps'])
        s=collections.defaultdict(float); c=collections.Counter()
        for r in d: s[r['hero']]+=r[tgt]-(b(r)-own.get(r['hero'],0.)); c[r['hero']]+=1
        own={h:s[h]/(c[h]+k) for h in c}
        s=collections.defaultdict(float); c=collections.Counter()
        for r in d:
            for h in r['opps']: s[h]+=r[tgt]-(b(r)-opp.get(h,0.)); c[h]+=1
        opp={h:s[h]/(c[h]+k) for h in c}
    return own,opp

for role,pos in POS.items():
    T=pooled_table(pos,50,1500)
    pool=[r for r in ROWS if r['bucket']=='STANDARD' and r['role']==role and r.get('last_hits_at_10') is not None]
    lane=[r for r in pool if r['shape'] in ('2v2','1v1')]
    accts=sorted({r['account'] for r in pool}); rnd=random.Random(9); rnd.shuffle(accts)
    fo={a:i%5 for i,a in enumerate(accts)}
    M={f: fit_ours([r for r in lane if fo[r['account']]!=f],'last_hits_at_10') for f in range(5)}
    HP=lambda r:(HS.get((r['hero'],r['pos'],10)) or {}).get('cs') if (HS.get((r['hero'],r['pos'],10)) or {}).get('matchCount',0)>=300 else None
    seq=collections.defaultdict(list)
    for r in pool: seq[r['account']].append(r)
    res=collections.defaultdict(list); n=0
    for a,rs in seq.items():
        rs=sorted(rs,key=lambda r:(r['started'] or 0,r['match_id']))
        own,opp=M[fo[a]]
        Eo=lambda r: None if r['shape'] not in ('2v2','1v1') else sum(opp.get(h,0.) for h in r['opps'])
        Es=lambda r: None if r['shape'] not in ('2v2','1v1') or any(h not in T for h in r['opps']) else sum(T[h] for h in r['opps'])
        for i,r in enumerate(rs):
            pr=rs[max(0,i-20):i]
            if len(pr)<5: continue
            eo,es=Eo(r),Es(r); hp=HP(r)
            qo=[x for x in (Eo(y) for y in pr) if x is not None]
            qs=[x for x in (Es(y) for y in pr) if x is not None]
            qh=[x for x in (HP(y) for y in pr) if x is not None]
            if eo is None or es is None or hp is None or min(len(qo),len(qs),len(qh))<3: continue
            n+=1
            b=st.median(x['last_hits_at_10'] for x in pr); y=r['last_hits_at_10']
            dh_o=own.get(r['hero'],0.)-st.median(own.get(x['hero'],0.) for x in pr)
            dh_s=hp-st.median(qh)
            res['A'].append(y-b)
            res['ours: hero+env'].append(y-(b+dh_o+eo-st.median(qo)))
            res['STRATZ: hero+env'].append(y-(b+dh_s+es-st.median(qs)))
            res['STRATZ hero + ours env'].append(y-(b+dh_s+eo-st.median(qo)))
            res['ours hero + STRATZ env'].append(y-(b+dh_o+es-st.median(qs)))
    vA=st.pvariance(res['A']); mA=st.fmean(abs(x) for x in res['A'])
    print(f"\n  {role}  n={n}  sdA={math.sqrt(vA):.2f}  MAE_A={mA:.3f}")
    for k in ('ours: hero+env','STRATZ: hero+env','STRATZ hero + ours env','ours hero + STRATZ env'):
        print(f"     {k:<26} variance {100*(1-st.pvariance(res[k])/vA):+6.2f}%   MAE {100*(1-st.fmean(abs(x) for x in res[k])/mA):+6.2f}%")
