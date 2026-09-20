"""Model B with OUR fitted hero effects vs Model B with STRATZ heroStats population means."""
import json, pickle, collections, statistics as st, random, math

HS = {(r['heroId'], r['position'], r['time']): r for r in json.load(open('herostats_pop.json'))}
ROWS = pickle.load(open('metrics.pkl', 'rb'))
FIELD = {'last_hits_at_10': ('cs', 10), 'net_worth_at_10': ('networth', 10),
         'deaths_before_10': ('deaths', 10)}

def fit_own(train, tgt, k=40.0, iters=4):
    ys=[r[tgt] for r in train]; g=sum(ys)/len(ys); own={}
    for _ in range(iters):
        s=collections.defaultdict(float); c=collections.Counter()
        for r in train:
            s[r['hero']] += r[tgt]-g; c[r['hero']]+=1
        own={h:s[h]/(c[h]+k) for h in c}
    return own

def run(tgt, role, bucket, folds=5, minprior=5, window=20, minmatch=300):
    f, t = FIELD[tgt]
    pool=[r for r in ROWS if r['role']==role and r['bucket']==bucket and r.get(tgt) is not None]
    if len(pool)<2000: return
    accts=sorted({r['account'] for r in pool}); rnd=random.Random(9); rnd.shuffle(accts)
    foldof={a:i%folds for i,a in enumerate(accts)}
    ourmodel={fd: fit_own([r for r in pool if foldof[r['account']]!=fd], tgt) for fd in range(folds)}
    def S(r):
        x=HS.get((r['hero'], r['pos'], t))
        if not x or (x.get('matchCount') or 0) < minmatch or x.get(f) is None: return None
        return x[f]
    seq=collections.defaultdict(list)
    for r in pool: seq[r['account']].append(r)
    res=collections.defaultdict(list); n=0; miss=0
    for a,rs in seq.items():
        rs=sorted(rs,key=lambda r:(r['started'] or 0, r['match_id']))
        own=ourmodel[foldof[a]]
        for i,r in enumerate(rs):
            prior=rs[max(0,i-window):i]
            if len(prior)<minprior: continue
            sc=S(r); sp=[S(x) for x in prior]; sp=[x for x in sp if x is not None]
            if sc is None or len(sp)<3: miss+=1; continue
            n+=1
            b=st.median(x[tgt] for x in prior)
            dOur=own.get(r['hero'],0.)-st.median(own.get(x['hero'],0.) for x in prior)
            dStr=sc-st.median(sp)
            res['A'].append(r[tgt]-b)
            res['B_ours'].append(r[tgt]-(b+dOur))
            res['B_stratz'].append(r[tgt]-(b+dStr))
            res['B_both'].append(r[tgt]-(b+0.5*dOur+0.5*dStr))
    if n<500: return
    vA=st.pvariance(res['A']); mA=st.fmean(abs(x) for x in res['A'])
    out=f"  {tgt:<20}{role:<9}{bucket:<9}n={n:<6}skipped={miss:<5}sdA={math.sqrt(vA):8.2f} |"
    for k in ('B_ours','B_stratz','B_both'):
        out+=f"  {k}: var{100*(1-st.pvariance(res[k])/vA):+6.1f}% mae{100*(1-st.fmean(abs(x) for x in res[k])/mA):+6.1f}%"
    print(out)

for bucket in ('STANDARD','TURBO'):
    print(f"\n--- {bucket}")
    for tgt in FIELD:
        for role in ('Carry','Mid','Offlane','Support'):
            run(tgt, role, bucket)
